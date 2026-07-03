# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ServiceCreditRate(models.Model):
    _name = 'service.credit.rate'
    _description = 'Service Credit Rate'

    name = fields.Char(compute='_compute_name', store=True)
    dimension = fields.Selection([
        ('employee', 'Employee'),
        ('job', 'Job position'),
        ('category', 'Employee category'),
    ], required=True)
    employee_id = fields.Many2one('hr.employee')
    job_id = fields.Many2one('hr.job')
    category_id = fields.Many2one('hr.employee.category')
    credits_per_hour = fields.Float(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('dimension', 'employee_id', 'job_id', 'category_id')
    def _compute_name(self):
        for record in self:
            if record.dimension == 'employee' and record.employee_id:
                record.name = f"Employee: {record.employee_id.name}"
            elif record.dimension == 'job' and record.job_id:
                record.name = f"Job: {record.job_id.name}"
            elif record.dimension == 'category' and record.category_id:
                record.name = f"Category: {record.category_id.name}"
            else:
                record.name = "Unknown"
