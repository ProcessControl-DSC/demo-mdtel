# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models
import pytz


class ResCompany(models.Model):
    _inherit = 'res.company'

    service_credit_default_rate = fields.Float(default=1.0)
    service_credit_time_mode = fields.Selection([
        ('manual', 'Manual selector'),
        ('auto', 'Automatic from datetime'),
        ('hybrid', 'Hybrid'),
    ], default='manual')
    service_credit_night_start = fields.Float(default=22.0)
    service_credit_night_end = fields.Float(default=6.0)
    service_credit_fallback_policy = fields.Selection([
        ('block', 'Block'),
        ('general', 'Use general wallet'),
        ('ask', 'Ask to select'),
    ], default='block')
    service_credit_enabled = fields.Boolean(default=False)
    service_credit_shortage_policy = fields.Selection([
        ('warn', 'Warn'),
        ('block', 'Block'),
        ('overdraft', 'Allow overdraft'),
    ], default='warn')
    service_credit_overdraft_limit = fields.Float(default=0.0)
    service_credit_deferred_enabled = fields.Boolean(default=False)
    service_credit_deferred_journal_id = fields.Many2one('account.journal')
    service_credit_deferred_account_id = fields.Many2one('account.account')
    service_credit_income_account_id = fields.Many2one('account.account')
    service_credit_value_per_credit = fields.Float(default=1.0)

    def service_credit_rate_for_employee(self, employee):
        self.ensure_one()
        ServiceCreditRate = self.env['service.credit.rate']
        rate = ServiceCreditRate.search([('company_id', '=', self.id), ('active', '=', True), ('dimension', '=', 'employee'), ('employee_id', '=', employee.id)], limit=1)
        if rate:
            return rate.credits_per_hour
        if employee.job_id:
            rate = ServiceCreditRate.search([('company_id', '=', self.id), ('active', '=', True), ('dimension', '=', 'job'), ('job_id', '=', employee.job_id.id)], limit=1)
            if rate:
                return rate.credits_per_hour
        if employee.category_ids:
            rate = ServiceCreditRate.search([('company_id', '=', self.id), ('active', '=', True), ('dimension', '=', 'category'), ('category_id', 'in', employee.category_ids.ids)], limit=1)
            if rate:
                return rate.credits_per_hour
        return self.service_credit_default_rate

    def service_credit_multiplier_for_bracket(self, bracket):
        self.ensure_one()
        multiplier = self.env['service.credit.multiplier'].search([('company_id', '=', self.id), ('active', '=', True), ('bracket', '=', bracket)], limit=1)
        return multiplier.factor if multiplier else 1.0

    def service_credit_convert(self, employee, hours, bracket='normal'):
        self.ensure_one()
        return hours * self.service_credit_rate_for_employee(employee) * self.service_credit_multiplier_for_bracket(bracket)

    def service_credit_classify_bracket(self, dt):
        self.ensure_one()
        cal = self.resource_calendar_id
        tz = pytz.timezone(cal.tz) if cal and cal.tz else pytz.UTC
        local = pytz.UTC.localize(dt).astimezone(tz)
        holiday = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('calendar_id', 'in', [cal.id, False] if cal else [False]),
            ('date_from', '<=', dt),
            ('date_to', '>=', dt),
        ], limit=1)
        if holiday:
            return 'holiday'
        dow = str(local.weekday())
        atts = cal.attendance_ids.filtered(lambda a: a.dayofweek == dow) if cal else self.env['resource.calendar.attendance']
        if not atts:
            return 'weekend'
        hour = local.hour + local.minute / 60.0
        for a in atts:
            if a.hour_from <= hour <= a.hour_to:
                return 'normal'
        ns = self.service_credit_night_start
        ne = self.service_credit_night_end
        if ns > ne:
            is_night = ns <= hour or hour < ne
        else:
            is_night = ns <= hour < ne
        return 'night' if is_night else 'after_hours'

    def _service_credit_general_wallet(self, partner):
        self.ensure_one()
        Wallet = self.env['service.credit.wallet']
        wallet = Wallet.search([('company_id', '=', self.id), ('partner_id', '=', partner.id), ('scope', '=', 'general')], limit=1)
        if not wallet:
            wallet = Wallet.create({'partner_id': partner.id, 'scope': 'general', 'company_id': self.id})
        return wallet
