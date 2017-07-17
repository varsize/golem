import json
import unittest
from os import urandom

from ethereum import tester, processblock
from ethereum.utils import int_to_big_endian, zpad

from golem.ethereum.contracts import TestGNT
from golem.utils import decode_hex, encode_hex

# FIXME: upgrade to pyethereum 2.x
setattr(processblock, 'unicode', str)

TEST_GNT_ABI = json.loads(TestGNT.ABI)


class TestGNTTest(unittest.TestCase):
    def setUp(self):
        self.state = tester.state()

    def deploy_contract(self):
        addr = self.state.evm(decode_hex(TestGNT.INIT_HEX))
        self.state.mine()
        return tester.ABIContract(self.state, TEST_GNT_ABI, addr)

    @staticmethod
    def encode_payments(payments):
        args = []
        value_sum = 0
        for idx, v in payments:
            addr = tester.accounts[idx]
            value_sum += v
            v = int(v)
            assert v < 2**96
            vv = zpad(int_to_big_endian(v), 12)
            mix = vv + addr
            assert len(mix) == 32
            print((encode_hex(mix), "v: ", v, "addr", encode_hex(addr)))
            args.append(mix)
        return args, value_sum

    def test_balance0(self):
        gnt = self.deploy_contract()
        b = gnt.balanceOf('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        assert b == 0

    def test_create(self):
        gnt = self.deploy_contract()

        assert gnt.totalSupply() == 0
        gnt.create(sender=tester.k0)
        assert gnt.balanceOf(tester.a0) == 1000 * 10**18
        assert gnt.totalSupply() == 1000 * 10**18

    def test_transfer(self):
        gnt = self.deploy_contract()
        gnt.create(sender=tester.k1)
        addr = encode_hex(urandom(20))
        value = 999 * 10**18
        sender_balance_before = self.state.block.get_balance(tester.a1)
        gnt.transfer(addr, value, sender=tester.k1)
        sender_balance_after = self.state.block.get_balance(tester.a1)
        assert gnt.balanceOf(addr) == value
        eth_cost = sender_balance_before - sender_balance_after
        gas_cost = eth_cost / tester.GAS_PRICE
        assert 50000 < gas_cost < 60000

    def test_batch_transfer(self):
        gnt = self.deploy_contract()
        gnt.create(sender=tester.k0)
        payments, v = self.encode_payments([(1, 1), (2, 2), (3, 3), (4, 4)])
        gnt.batchTransfer(payments, sender=tester.k0)
        assert gnt.balanceOf(tester.a1) == 1
        assert gnt.balanceOf(tester.a2) == 2
        assert gnt.balanceOf(tester.a3) == 3
        assert gnt.balanceOf(tester.a4) == 4
        assert gnt.balanceOf(tester.a0) == 1000 * 10**18 - v
