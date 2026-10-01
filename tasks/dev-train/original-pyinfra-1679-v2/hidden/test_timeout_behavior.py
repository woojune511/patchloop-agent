"""Operator-only behavioral checks; never project into solving-agent context."""

import io
import sys
import unittest
from unittest.mock import Mock, patch

from paramiko import HostKeys, SSHConfig
from pyinfra.connectors.sshuserclient import client as m


class TimeoutBehavior(unittest.TestCase):
    def observe(self, target_timeout=None, hop_timeout=None, kwargs=None, proxy=True):
        self.assertTrue(m.__file__.startswith("/workspace/src/"), m.__file__)
        text = "Host jump\n HostName jump.example\n User jumper\n"
        if hop_timeout is not None:
            text += f" ConnectTimeout {hop_timeout}\n"
        text += "Host device\n HostName target.example\n User user\n"
        if proxy:
            text += " ProxyJump jump\n"
        if target_timeout is not None:
            text += f" ConnectTimeout {target_timeout}\n"
        config = SSHConfig()
        config.parse(io.StringIO(text))
        connections, channels = [], []

        def connect(client, hostname, **args):
            connections.append((hostname, args))

        def open_channel(kind, destination, origin, timeout=None):
            channels.append((kind, destination, origin, timeout))
            return Mock()

        transport = Mock()
        transport.open_channel.side_effect = open_channel
        with (
            patch.object(m, "get_ssh_config", return_value=config),
            patch.object(m, "get_host_keys", return_value=HostKeys()),
            patch.object(m.ParamikoClient, "connect", connect),
            patch.object(m.SSHClient, "get_transport", return_value=transport),
        ):
            m.SSHClient().connect("device", **(kwargs or {}))
        self.assertEqual(
            [host for host, _ in connections],
            ["jump.example", "target.example"] if proxy else ["target.example"],
        )
        self.assertEqual(len(channels), int(proxy))
        if proxy:
            self.assertEqual(channels[0][0:2], ("direct-tcpip", ("target.example", 22)))
        return [args for _, args in connections], channels

    def test_target_configuration(self):
        connections, channels = self.observe(target_timeout=5)
        self.assertEqual(connections[-1].get("timeout"), 5)
        self.assertEqual(channels[0][-1], 5)

    def test_hop_configuration_is_independent(self):
        connections, channels = self.observe(target_timeout=5, hop_timeout=7)
        self.assertEqual([c.get("timeout") for c in connections], [7, 5])
        self.assertEqual(channels[0][-1], 5)

    def test_explicit_override_precedes_default_and_configuration(self):
        overrides = dict(timeout=2, auth_timeout=2, banner_timeout=2, channel_timeout=2)
        connections, channels = self.observe(
            target_timeout=5, hop_timeout=7,
            kwargs={"timeout": 10, "_pyinfra_ssh_paramiko_connect_kwargs": overrides},
        )
        self.assertEqual(connections[0].get("timeout"), 7)
        for key, value in overrides.items():
            self.assertEqual(connections[-1].get(key), value)
        self.assertEqual(channels[0][-1], 2)

    def test_direct_kwarg_precedes_configuration(self):
        connections, channels = self.observe(target_timeout=5, kwargs={"timeout": 2})
        self.assertEqual(connections[-1].get("timeout"), 2)
        self.assertEqual(channels[0][-1], 2)

    def test_absent_timeout_keeps_default(self):
        connections, channels = self.observe()
        self.assertEqual([c.get("timeout") for c in connections], [None, None])
        self.assertIsNone(channels[0][-1])

    def test_direct_host_configuration(self):
        connections, channels = self.observe(target_timeout=12, proxy=False)
        self.assertEqual(connections[0].get("timeout"), 12)
        self.assertEqual(channels, [])

    def test_gateway_effective_timeout(self):
        cases = [({}, None), ({"timeout": None}, None), ({"timeout": 0}, 0), ({"timeout": 2}, 2)]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                calls = []
                sentinel = object()

                def open_channel(kind, destination, origin, timeout=None,
                                 calls=calls, sentinel=sentinel):
                    calls.append((kind, destination, origin, timeout))
                    return sentinel

                transport = Mock()
                transport.open_channel.side_effect = open_channel
                with patch.object(m.SSHClient, "get_transport", return_value=transport):
                    result = m.SSHClient().gateway("jump", 22, "target", 23, **kwargs)
                self.assertIs(result, sentinel)
                self.assertEqual(calls, [("direct-tcpip", ("target", 23), ("jump", 22), expected)])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TimeoutBehavior)
    )
    sys.exit(0 if result.wasSuccessful() else 1)
