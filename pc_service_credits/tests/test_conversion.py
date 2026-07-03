# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests.common import TransactionCase


class TestServiceCreditConversion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.service_credit_default_rate = 1.0
        cls.job = cls.env['hr.job'].create({'name': 'Technician'})
        cls.category = cls.env['hr.employee.category'].create({'name': 'Field'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Alice',
            'job_id': cls.job.id,
            'category_ids': [(6, 0, cls.category.ids)],
            'company_id': cls.company.id,
        })
        cls.Rate = cls.env['service.credit.rate']
        cls.Mult = cls.env['service.credit.multiplier']

    def _rate(self, dimension, cph, **kw):
        vals = {'dimension': dimension, 'credits_per_hour': cph, 'company_id': self.company.id}
        vals.update(kw)
        return self.Rate.create(vals)

    def test_cascade_employee_wins(self):
        self._rate('category', 10, category_id=self.category.id)
        self._rate('job', 15, job_id=self.job.id)
        self._rate('employee', 30, employee_id=self.employee.id)
        self.assertEqual(
            self.company.service_credit_rate_for_employee(self.employee), 30)

    def test_cascade_job_when_no_employee(self):
        self._rate('category', 10, category_id=self.category.id)
        self._rate('job', 15, job_id=self.job.id)
        self.assertEqual(
            self.company.service_credit_rate_for_employee(self.employee), 15)

    def test_cascade_category_when_no_job(self):
        self._rate('category', 10, category_id=self.category.id)
        self.assertEqual(
            self.company.service_credit_rate_for_employee(self.employee), 10)

    def test_default_when_no_rate(self):
        self.assertEqual(
            self.company.service_credit_rate_for_employee(self.employee), 1.0)

    def test_multiplier_lookup(self):
        self.Mult.create({'bracket': 'after_hours', 'factor': 1.5,
                          'company_id': self.company.id})
        self.assertEqual(
            self.company.service_credit_multiplier_for_bracket('after_hours'), 1.5)
        self.assertEqual(
            self.company.service_credit_multiplier_for_bracket('night'), 1.0)

    def test_convert_role_and_bracket(self):
        self._rate('employee', 30, employee_id=self.employee.id)
        self.Mult.create({'bracket': 'after_hours', 'factor': 1.5,
                          'company_id': self.company.id})
        self.assertEqual(
            self.company.service_credit_convert(self.employee, 2.0, 'after_hours'), 90.0)
        self.assertEqual(
            self.company.service_credit_convert(self.employee, 2.0, 'normal'), 60.0)
