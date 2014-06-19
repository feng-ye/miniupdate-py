#!/usr/bin/env python

# This is a script to update dynamic DNS service (minidns.net)
# using the protocol described in:
#   http://www.3open.org/d/ddns/ddns

import asyncore
import asynchat
import socket
import hashlib
import argparse

AGENT = "miniupdate-py/1.0"
DEFAULT_UPDATE_SERVER = "update.minidns.net"
DEFAULT_UPDATE_PORT = 9120

def get_digest(passwd, salt):
    m = hashlib.md5()
    m.update(passwd)
    p = m.hexdigest()

    m = hashlib.md5()
    m.update(p)
    m.update(salt)
    return m.hexdigest()


class DDNSUpdater(asynchat.async_chat):
    def __init__(self, config):
        asynchat.async_chat.__init__(self)
        self.config = config
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((config['server'], config['port']))
        self.set_terminator("\n")
        self.data = ""
        self.nextcmd = "AGENT"

    def collect_incoming_data(self, data):
        self.data += data

    def found_terminator(self):
        print ">>", self.data

        res = self.data.split()
        if res[0] == "OK":
            if self.nextcmd == "LOGIN":
                user = self.config["user"]
                self.send_msg(self.nextcmd, user, "digest-md5-text")
                self.nextcmd = "RESPONSE"

            elif self.nextcmd == "A_UPDATE":
                hostname = self.config["hostname"]
                on_off = self.config.get("mode", "online")
                ip = self.config.get("ip", None)
                if ip:
                    self.send_msg(self.nextcmd, on_off, hostname, ip)
                else:
                    self.send_msg(self.nextcmd, on_off, hostname)
                self.nextcmd = "EXIT"

            elif self.nextcmd == "VERSION":
                self.send_msg(self.nextcmd)
                self.nextcmd = "LOGIN"

            elif self.nextcmd == "EXIT":
                self.send_msg(self.nextcmd)
                self.nextcmd = None

            else:
                self.close()

        if res[0] == "ERR":
            self.close()

        if res[0] == "CHALLENGE":
            passwd = self.config["passwd"]
            self.send_msg(self.nextcmd, get_digest(passwd, res[1]))
            self.nextcmd = "A_UPDATE"
            # self.nextcmd = "EXIT"

        else:
            pass

        self.data = ""

    def send_msg(self, *args):
        msg = " ".join(args)
        print "<<", msg
        self.send(msg+"\n")

    def handle_connect(self):
        agent = self.config.get("agent", AGENT)
        self.send_msg("AGENT", agent)
        self.nextcmd = "VERSION"


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-s", dest="server", help="update server name")
        parser.add_argument("-p", dest="port", help="update server port")
        parser.add_argument("-c", dest="cfile", help="config file")
        parser.add_argument("-u", dest="user", help="user name")
        parser.add_argument("-P", dest="passwd", help="password")
        parser.add_argument("-i", dest="ip", help="ip of hostname")
        parser.add_argument("-m", dest="mode", choices=["online", "offline"],
                default="online", help="online/offline")
        parser.add_argument("hostname", nargs="?", help="hostname to update")
        args = parser.parse_args()

        config = {}
        if args.cfile:
            execfile(args.cfile, globals(), config)

        if args.server:
            config["server"] = args.server
        else:
            config.setdefault("server", DEFAULT_UPDATE_SERVER)

        if args.port:
            config["port"] = args.port
        else:
            config.setdefault("port", DEFAULT_UPDATE_PORT)

        if args.user:
            config["user"] = args.user
        if args.passwd:
            config["passwd"] = args.passwd

        if not config.get("passwd", None) or not config.get("user", None):
            print "Error: no user or password."
            return

        if args.hostname:
            config["hostname"] = args.hostname
        if not config.get("hostname", None):
            print "Error: no hostname to update"
            return

        if args.ip:
            config["ip"] = args.ip

        if args.mode:
            config["mode"] = args.mode
        else:
            config.setdefault("mode", "online")

        DDNSUpdater(config)
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

