# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestServiceCreditDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.service_credit_enabled = True
        cls.company.service_credit_default_rate = 10.0
        cls.company.service_credit_shortage_policy = 'warn'
        cls.partner = cls.env['res.partner'].create({'name': 'Client Dash'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Tech Dash', 'company_id': cls.company.id})
        cls.wallet = cls.env['service.credit.wallet'].create({
            'partner_id': cls.partner.id, 'scope': 'general', 'company_id': cls.company.id})
        cls.project = cls.env['project.project'].create({
            'name': 'Maint Dash', 'partner_id': cls.partner.id,
            'credit_wallet_target_id': cls.wallet.id})
        cls.task = cls.env['project.task'].create({'name': 'T', 'project_id': cls.project.id})
        cls.env['service.credit.move'].create({
            'wallet_id': cls.wallet.id, 'move_type': 'topup', 'credit_amount': 100.0})

    def test_related_dimensions(self):
        line = self.env['account.analytic.line'].create({
            'name': 'w', 'project_id': self.project.id, 'task_id': self.task.id,
            'employee_id': self.employee.id, 'unit_amount': 2.0})
        move = line.credit_move_ids
        self.assertEqual(move.origin_employee_id, self.employee)
        self.assertEqual(move.origin_project_id, self.project)
        self.assertEqual(move.origin_bracket, 'normal')

    def test_burn_rate_and_runout(self):
        self.env['account.analytic.line'].create({
            'name': 'w', 'project_id': self.project.id, 'task_id': self.task.id,
            'employee_id': self.employee.id, 'unit_amount': 2.0})  # -20
        self.assertAlmostEqual(self.wallet.balance, 80.0)
        self.assertGreater(self.wallet.burn_rate, 0.0)
        self.assertTrue(self.wallet.runout_date)
