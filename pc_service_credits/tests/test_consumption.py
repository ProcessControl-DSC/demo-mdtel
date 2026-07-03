# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestServiceCreditConsumption(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.service_credit_enabled = True
        cls.company.service_credit_default_rate = 10.0
        cls.company.service_credit_time_mode = 'manual'
        cls.partner = cls.company.partner_id
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Tech', 'company_id': cls.company.id})
        cls.wallet = cls.env['service.credit.wallet'].create({
            'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.project = cls.env['project.project'].create({
            'name': 'Maint', 'partner_id': cls.partner.id,
            'credit_wallet_target_id': cls.wallet.id})
        cls.task = cls.env['project.task'].create({
            'name': 'Fix', 'project_id': cls.project.id})

    def _topup(self, amount):
        self.env['service.credit.move'].create({
            'wallet_id': self.wallet.id, 'move_type': 'topup', 'credit_amount': amount})

    def _timesheet(self, hours):
        return self.env['account.analytic.line'].create({
            'name': 'work', 'project_id': self.project.id, 'task_id': self.task.id,
            'employee_id': self.employee.id, 'unit_amount': hours})

    def test_consumption_sufficient(self):
        self._topup(100)
        self.company.service_credit_shortage_policy = 'block'
        line = self._timesheet(2.0)  # 2h * 10 = 20
        self.assertEqual(len(line.credit_move_ids), 1)
        self.assertEqual(line.credit_move_ids.credit_amount, -20.0)
        self.assertAlmostEqual(self.wallet.balance, 80.0)

    def test_block_on_shortage(self):
        self._topup(5)
        self.company.service_credit_shortage_policy = 'block'
        with self.assertRaises(UserError):
            self._timesheet(2.0)  # needs 20 > 5

    def test_overdraft_within_limit(self):
        self.company.service_credit_shortage_policy = 'overdraft'
        self.company.service_credit_overdraft_limit = 50.0
        line = self._timesheet(2.0)  # -20, projected -20 >= -50 -> allowed
        self.assertAlmostEqual(self.wallet.balance, -20.0)
        self.assertEqual(len(line.credit_move_ids), 1)

    def test_overdraft_exceeded(self):
        self.company.service_credit_shortage_policy = 'overdraft'
        self.company.service_credit_overdraft_limit = 10.0
        with self.assertRaises(UserError):
            self._timesheet(2.0)  # -20 < -10 limit

    def test_warn_allows_and_notifies(self):
        self.company.service_credit_shortage_policy = 'warn'
        before = len(self.wallet.message_ids)
        line = self._timesheet(1.0)  # -10, balance 0 -> negative, warn
        self.assertAlmostEqual(self.wallet.balance, -10.0)
        self.assertEqual(len(line.credit_move_ids), 1)
        self.assertGreater(len(self.wallet.message_ids), before)

    def test_recompute_on_write(self):
        self._topup(100)
        self.company.service_credit_shortage_policy = 'warn'
        line = self._timesheet(2.0)  # -20 -> balance 80
        self.assertAlmostEqual(self.wallet.balance, 80.0)
        line.write({'unit_amount': 3.0})  # recompute -> -30 -> balance 70
        self.assertEqual(len(line.credit_move_ids), 1)
        self.assertEqual(line.credit_move_ids.credit_amount, -30.0)
        self.assertAlmostEqual(self.wallet.balance, 70.0)

    def test_disabled_company_no_move(self):
        self.company.service_credit_enabled = False
        line = self._timesheet(2.0)
        self.assertEqual(len(line.credit_move_ids), 0)
