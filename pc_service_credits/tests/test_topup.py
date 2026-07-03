# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestServiceCreditTopup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.service_credit_enabled = True
        cls.partner = cls.env['res.partner'].create({'name': 'Client Bono'})
        cls.bono = cls.env['product.product'].create({
            'name': 'Bono 100 créditos', 'type': 'service',
            'is_service_credit_bono': True, 'service_credit_granted': 100.0})

    def _confirm_sale(self, qty=1):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': self.bono.id, 'product_uom_qty': qty})],
        })
        so.action_confirm()
        return so

    def test_topup_on_confirm(self):
        so = self._confirm_sale(qty=1)
        wallet = self.company._service_credit_general_wallet(self.partner)
        self.assertAlmostEqual(wallet.balance, 100.0)
        move = self.env['service.credit.move'].search([('sale_line_id', '=', so.order_line.id)])
        self.assertEqual(move.move_type, 'topup')

    def test_topup_idempotent(self):
        so = self._confirm_sale(qty=1)
        so._service_credit_generate_topups()  # re-run
        moves = self.env['service.credit.move'].search([('sale_line_id', '=', so.order_line.id)])
        self.assertEqual(len(moves), 1)

    def test_fifo_expiry(self):
        wallet = self.env['service.credit.wallet'].create({
            'partner_id': self.partner.id, 'scope': 'general', 'company_id': self.company.id})
        today = date(2026, 7, 3)
        Move = self.env['service.credit.move']
        Move.create({'wallet_id': wallet.id, 'move_type': 'topup', 'credit_amount': 100.0,
                     'lot_date': today - timedelta(days=400), 'expiry_date': today - timedelta(days=10)})
        Move.create({'wallet_id': wallet.id, 'move_type': 'topup', 'credit_amount': 50.0,
                     'lot_date': today - timedelta(days=5), 'expiry_date': today + timedelta(days=30)})
        Move.create({'wallet_id': wallet.id, 'move_type': 'consumption', 'credit_amount': -30.0})
        self.assertAlmostEqual(wallet.balance, 120.0)
        wallet._service_credit_expire_fifo(today)
        # lot A (100) had 30 consumed -> 70 remaining, expired -> expiry -70
        expiries = Move.search([('wallet_id', '=', wallet.id), ('move_type', '=', 'expiry')])
        self.assertEqual(len(expiries), 1)
        self.assertAlmostEqual(expiries.credit_amount, -70.0)
        self.assertAlmostEqual(wallet.balance, 50.0)
        # idempotent second run
        wallet._service_credit_expire_fifo(today)
        expiries2 = Move.search([('wallet_id', '=', wallet.id), ('move_type', '=', 'expiry')])
        self.assertEqual(len(expiries2), 1)
        self.assertAlmostEqual(wallet.balance, 50.0)
