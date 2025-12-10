from odoo import http, _, exceptions, fields
from odoo.http import request

class RekapTitipanController(http.Controller):
    @http.route('/breeze_distribution/get/rekap/titipan', csrf=False, auth='user', methods=['POST'], type='json')
    def getRekapTitipan(self, **kw):

        user = request.env.user
        employee = request.env['hr.employee'].search([
            ('user_id', '=', user.id)
        ])
        if len(employee) == 0:
            raise exceptions.ValidationError('User belum memiliki entitas employee')
        
        employee = employee[0]

        today = fields.Date.today()
        rekap = request.env['breeze_distribution.rekap_titipan'].search([
            ("employee_id",'=',employee.id),
            ("tanggal",'=',today)
        ])

         
        
        listRekap =[]

        for x in rekap:
            listRekap.append({
                "id" : x.id,
                "tanggal":x.tanggal,
                "employee" : x.employee_id.name,
                "invoice" : {
                    'name' : x.invoice_id.name,
                    'customer': x.invoice_id.partner_id.name
                },
                "jumlah" : x.jumlah,
                "metode" : x.metode
            })

        return listRekap

        