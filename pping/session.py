# -*- coding: utf-8 -*-


import select
import socket
import threading
import time
from collections import namedtuple

from .packet import Icmp, IPv4


class Request:

    @staticmethod
    def ping(*, address, repeat, interval, size, timeout, ttl):
        with socket.socket(socket.AF_INET,
                           socket.SOCK_RAW,
                           socket.IPPROTO_ICMP) as conn:
            conn.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            try:
                conn.connect((address, 0))
            except OSError as e:
                err_msg = (
                    f'An error occurred while connecting to: [{address}]\n'
                    f'> {e}'
                )
                print(err_msg)
                return None
            else:
                id_ = threading.get_ident()
                result = list()
                for seq in range(1, repeat + 1):
                    packet = Icmp.pack(id_=id_, seq=seq, size=size)
                    response = Request.ping_once(conn, packet, timeout)
                    result.append(response)
                    if seq < repeat:
                        time.sleep(interval)
                return result

    @staticmethod
    def ping_once(conn, packet, timeout):
        try:
            send_time = time.time()
            conn.send(packet)
            while True:
                readable, _, _ = select.select([conn], [], [], timeout)
                recv_packet = readable[0].recv(1024)
                rtt = time.time() - send_time
                return Response.valid(packet=recv_packet, rtt=rtt)
        except IndexError:
            return Response.timeout()


class Response:

    OK, TIMEDOUT = 'ok', 'timedout'

    _Valid = namedtuple('Response', ['status', 'src', 'dst', 'ttl',
                                     'size', 'seq', 'rtt'])

    _Error = namedtuple('Response', ['status'])

    @staticmethod
    def valid(*, packet, rtt):
        ipv4 = IPv4.unpack(packet[:20])
        icmp = Icmp.unpack(packet[20:])
        return Response._Valid(Response.OK, ipv4.src, ipv4.dst, ipv4.ttl,
                               len(icmp.payload), icmp.seq, rtt)

    @staticmethod
    def timeout():
        return Response._Error(Response.TIMEDOUT)