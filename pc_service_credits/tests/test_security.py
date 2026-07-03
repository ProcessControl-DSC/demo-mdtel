# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestServiceCreditSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base_user = cls.env.ref('base.group_user')
        g_user = cls.env.ref('pc_service_credits.group_service_credit_user')
        g_mgr = cls.env.ref('pc_service_credits.group_service_credit_manager')
        cls.u_user = cls.env['res.users'].create({
            'name': 'SC User', 'login': 'sc_user',
            'group_ids': [(6, 0, [base_user.id, g_user.id])]})
        cls.u_mgr = cls.env['res.users'].create({
            'name': 'SC Manager', 'login': 'sc_mgr',
            'group_ids': [(6, 0, [base_user.id, g_mgr.id])]})

    def test_user_cannot_create_rate(self):
        with self.assertRaises(AccessError):
            self.env['service.credit.rate'].with_user(self.u_user).create({
                'dimension': 'employee', 'credits_per_hour': 5.0})

    def test_manager_can_create_rate(self):
        rate = self.env['service.credit.rate'].with_user(self.u_mgr).create({
            'dimension': 'employee', 'credits_per_hour': 5.0})
        self.assertTrue(rate.id)

    def test_user_can_read_wallet(self):
        # no debe lanzar
        self.env['service.credit.wallet'].with_user(self.u_user).search([])

    def test_user_cannot_create_wallet(self):
        with self.assertRaises(AccessError):
            self.env['service.credit.wallet'].with_user(self.u_user).create({
                'partner_id': self.env.company.partner_id.id, 'scope': 'general'})
