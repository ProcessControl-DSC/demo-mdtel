# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import date, datetime, timedelta

from odoo.tests.common import TransactionCase


class TestServiceCreditClassify(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.cal = cls.company.resource_calendar_id
        # deterministic timezone so local == UTC
        cls.cal.tz = 'UTC'
        cls.company.service_credit_night_start = 22.0
        cls.company.service_credit_night_end = 6.0
        # ensure standard weekday attendance exists (Mon-Fri 08-12, 13-17)
        if not cls.cal.attendance_ids:
            att = []
            for d in '01234':
                att += [
                    (0, 0, {'name': 'M', 'dayofweek': d, 'hour_from': 8.0, 'hour_to': 12.0}),
                    (0, 0, {'name': 'A', 'dayofweek': d, 'hour_from': 13.0, 'hour_to': 17.0}),
                ]
            cls.cal.attendance_ids = att
        # find a deterministic Monday
        d0 = date(2026, 7, 6)
        while d0.weekday() != 0:
            d0 += timedelta(days=1)
        cls.monday = d0
        cls.saturday = d0 + timedelta(days=5)

    def _dt(self, d, h):
        return datetime(d.year, d.month, d.day, h, 0, 0)

    def test_normal_working_hours(self):
        self.assertEqual(
            self.company.service_credit_classify_bracket(self._dt(self.monday, 10)), 'normal')

    def test_after_hours(self):
        self.assertEqual(
            self.company.service_credit_classify_bracket(self._dt(self.monday, 19)), 'after_hours')

    def test_night(self):
        self.assertEqual(
            self.company.service_credit_classify_bracket(self._dt(self.monday, 23)), 'night')

    def test_weekend(self):
        self.assertEqual(
            self.company.service_credit_classify_bracket(self._dt(self.saturday, 10)), 'weekend')

    def test_holiday_priority(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'calendar_id': self.cal.id,
            'date_from': self._dt(self.monday, 0),
            'date_to': self._dt(self.monday, 23),
        })
        self.assertEqual(
            self.company.service_credit_classify_bracket(self._dt(self.monday, 10)), 'holiday')

    def test_line_bracket_manual_mode(self):
        self.company.service_credit_time_mode = 'manual'
        line = self.env['account.analytic.line'].new({
            'name': 't', 'credit_time_bracket': 'weekend'})
        self.assertEqual(line._service_credit_bracket(), 'weekend')
