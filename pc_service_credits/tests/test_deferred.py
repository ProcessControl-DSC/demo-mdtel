# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestServiceCreditDeferred(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.service_credit_enabled = True
        cls.company.service_credit_default_rate = 10.0
        cls.partner = cls.env['res.partner'].create({'name': 'Client Def'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Tech D', 'company_id': cls.company.id})
        cls.wallet = cls.env['service.credit.wallet'].create({
            'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.project = cls.env['project.project'].create({
            'name': 'Maint D', 'partner_id': cls.partner.id,
            'credit_wallet_target_id': cls.wallet.id})
        cls.task = cls.env['project.task'].create({'name': 'Fix D', 'project_id': cls.project.id})
        # accounting setup
        cls.deferred = cls.env['account.account'].create({
            'name': 'Deferred SC', 'code': 'SCDEF', 'account_type': 'liability_current'})
        cls.income = cls.env['account.account'].create({
            'name': 'Income SC', 'code': 'SCINC', 'account_type': 'income'})
        cls.journal = cls.env['account.journal'].create({
            'name': 'SC Journal', 'code': 'SCJ', 'type': 'general'})
        cls.env['service.credit.move'].create({
            'wallet_id': cls.wallet.id, 'move_type': 'topup', 'credit_amount': 1000.0})

    def _timesheet(self, hours=1.0):
        return self.env['account.analytic.line'].create({
            'name': 'work', 'project_id': self.project.id, 'task_id': self.task.id,
            'employee_id': self.employee.id, 'unit_amount': hours})

    def test_deferred_disabled_no_entry(self):
        self.company.service_credit_deferred_enabled = False
        line = self._timesheet(1.0)
        self.assertFalse(line.credit_move_ids.account_move_id)

    def test_deferred_posts_balanced_entry(self):
        self.company.write({
            'service_credit_deferred_enabled': True,
            'service_credit_deferred_journal_id': self.journal.id,
            'service_credit_deferred_account_id': self.deferred.id,
            'service_credit_income_account_id': self.income.id,
            'service_credit_value_per_credit': 2.0,
        })
        line = self._timesheet(1.0)  # 10 créditos * 2 €/crédito = 20
        move = line.credit_move_ids
        am = move.account_move_id
        self.assertTrue(am)
        self.assertEqual(am.state, 'posted')
        deferred_line = am.line_ids.filtered(lambda l: l.account_id == self.deferred)
        income_line = am.line_ids.filtered(lambda l: l.account_id == self.income)
        self.assertAlmostEqual(deferred_line.debit, 20.0)
        self.assertAlmostEqual(income_line.credit, 20.0)
