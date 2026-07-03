# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestServiceCreditRouting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.company.partner_id
        Wallet = cls.env['service.credit.wallet']
        cls.w_line = Wallet.create({'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.w_task = Wallet.create({'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.w_proj = Wallet.create({'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.project = cls.env['project.project'].create({
            'name': 'Maint', 'partner_id': cls.partner.id})
        cls.task = cls.env['project.task'].create({
            'name': 'Fix', 'project_id': cls.project.id})
        cls.AAL = cls.env['account.analytic.line']

    def _line(self, **kw):
        vals = {'name': 'work', 'company_id': self.company.id}
        vals.update(kw)
        return self.AAL.new(vals)

    def test_override_wins(self):
        self.project.credit_wallet_target_id = self.w_proj
        self.task.credit_wallet_target_id = self.w_task
        line = self._line(project_id=self.project.id, task_id=self.task.id,
                          credit_wallet_id=self.w_line.id)
        self.assertEqual(line._service_credit_resolve_wallet(), self.w_line)

    def test_task_over_project(self):
        self.project.credit_wallet_target_id = self.w_proj
        self.task.credit_wallet_target_id = self.w_task
        line = self._line(project_id=self.project.id, task_id=self.task.id)
        self.assertEqual(line._service_credit_resolve_wallet(), self.w_task)

    def test_project_when_no_task_target(self):
        self.project.credit_wallet_target_id = self.w_proj
        self.task.credit_wallet_target_id = False
        line = self._line(project_id=self.project.id, task_id=self.task.id)
        self.assertEqual(line._service_credit_resolve_wallet(), self.w_proj)

    def test_fallback_general_creates(self):
        self.company.service_credit_fallback_policy = 'general'
        p2 = self.env['res.partner'].create({'name': 'Client X'})
        line = self._line(partner_id=p2.id)
        wallet = line._service_credit_resolve_wallet()
        self.assertTrue(wallet)
        self.assertEqual(wallet.partner_id, p2)
        self.assertEqual(wallet.scope, 'general')

    def test_fallback_block_returns_empty(self):
        self.company.service_credit_fallback_policy = 'block'
        p3 = self.env['res.partner'].create({'name': 'Client Y'})
        line = self._line(partner_id=p3.id)
        self.assertFalse(line._service_credit_resolve_wallet())
