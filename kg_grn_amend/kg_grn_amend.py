""" GRN Amendment """
import time
from odoo import api, fields, models
from odoo.exceptions import UserError


class KgGrnAmend(models.Model):
    """ Kg GRN Amendment """
    _name = "kg.grn.amend"
    _description = "GRN Amend"
    _order = "crt_date desc"

    #### Selection fields declaration ###
    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('confirmed', 'WFA'),
        ('wfa_mgmt', 'WFA MGMT'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')]

    ENTRYMODE_SELECTION = [('auto', 'Auto'), ('manual', 'Manual')]

    # Basic Info

    name = fields.Many2one('kg.grn', 'GRN No', required=True, domain=[
                           ('state', 'in', ['confirmed', 'approved'])])
    entry_date = fields.Date(
        'GRN Date',
        required=True, readonly=True)
    entry_type = fields.Selection([('direct',
                                    'Direct'),
                                   ('from_po',
                                    'From PO'),
                                   ('from_so',
                                    'From SO'),
                                   ('from_gp',
                                    'From Gate Pass'),
                                   ('from_pi',
                                    'From PI'),
                                   ('from_mr',
                                    'From MR')],
                                  'Mode of GRN',
                                  required=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner',
        'Supplier Name',
        domain=[
            ('active_trans',
             '=',
             True),
            ('state',
             '=',
             'approved'),
            ('active',
             '=',
             True)],
        readonly=True)

    division_id = fields.Many2one(
        'kg.division.master', 'Division', readonly=True, domain=[
            ('state', 'in', ['approved'])])
    department_id = fields.Many2one(
        'hr.department', 'Department', readonly=True, domain=[
            ('state', 'in', ['approved'])])

    state = fields.Selection(
        STATE_SELECTION,
        'Status',
        readonly=True,
        default='draft')
    amendment_reason = fields.Text('Amendment Reason', required=True)
    entry_mode = fields.Selection(
        ENTRYMODE_SELECTION,
        'Entry Mode',
        readonly=True,
        default='manual')

    ### Entry Info ###
    company_id = fields.Many2one(
        'res.company',
        'Company Name',
        readonly=True,
        default=lambda self: self.env.user.company_id)
    active = fields.Boolean('Active', default=True)
    user_id = fields.Many2one(
        'res.users',
        'Created By',
        readonly=True,
        default=lambda self: self.env.user.id)
    crt_date = fields.Datetime(
        'Created Date',
        readonly=True,
        default=lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'))
    confirm_date = fields.Datetime('Confirmed Date', readonly=True)
    confirm_user_id = fields.Many2one(
        'res.users', 'Confirmed By', readonly=True)
    approved_date = fields.Datetime('Approved Date', readonly=True)
    approved_user_id = fields.Many2one(
        'res.users', 'Approved By', readonly=True)
    md_ap_rej_date = fields.Datetime('MGMT Approved Date', readonly=True)
    md_ap_rej_user_id = fields.Many2one(
        'res.users', 'MGMT Approved By', readonly=True)
    rejected_by = fields.Many2one(
        'res.users',
        'Rejected By',
        readonly=True)
    rejected_date = fields.Datetime(
        'Rejected Date',readonly=True)
    rejected_remark = fields.Text('Rejection Remarks')
    update_date = fields.Datetime('Last Updated Date', readonly=True)
    update_user_id = fields.Many2one(
        'res.users', 'Last Updated By', readonly=True)
    active_rpt = fields.Boolean('Visible in Report', default=True)
    active_trans = fields.Boolean('Visible in Transactions', default=True)

    # Child Tables Declaration
    line_ids = fields.One2many(
        'ch.grn.amend.line',
        'header_id',
        'GRN Details', readonly=True)

    @api.multi
    def validations(self):
        """GRN Amend Validation"""
        if self.line_ids:
            for line in self.line_ids:
                if not line.amend_inward_id:
                    raise UserError(
                        ('Kindly add amend inward type to proceed further'))

        if self.amendment_reason:
           if self.amendment_reason.isspace():
              raise UserError("Minimum 10 characters are required amendment reason")
           if " " in self.amendment_reason:
              amendment_reson = self.amendment_reason.replace(" ","")
              if len(self.amendment_reason) < 10:
                 raise UserError("Minimum 10 characters are required for amendment reason")
           else:
              if len(self.amendment_reason) < 10:
                 raise UserError(('Minimum 10 characters is must for amendment reason'))

        if self.name:
            if self.env['kg.purchase.invoice'].search([('grn_no', '=', self.name.name),('state', 'not in', ['draft'])]):
               raise UserError(
                    ('Purchase Invoice not in draft state.'))
            if self.env['kg.department.issue'].search([('grn_no', '=', self.name.name),('state', 'not in', ['draft'])]):
               raise UserError(
                    ('Item Issue not in draft state.'))

        if not self.line_ids:
                raise UserError(
                    ('Cannot confirm GRN Details with empty line items'))


    @api.onchange('name')
    def change_grn_id(self):
        """Onchange GRN"""
        grn_amend_line = []
        if self.name:
            self.env.cr.execute(""" select id from kg_department_issue
                   where state in ('approved', 'confirmed') and grn_no = '%s' """ % (self.name.name))
            issue = self.env.cr.fetchone()
            if issue:
                raise UserError(
                    ('Warning ,Issue confirmation or approval done against to this GRN'))

            self.env.cr.execute(""" select id from kg_purchase_invoice
                   where state in ('approved', 'confirmed') and grn_no = '%s' """ % (self.name.name))
            issue = self.env.cr.fetchone()
            if issue:
                raise UserError(
                    ('Warning ,PJV confirmation or approval done against to this GRN'))

            grn = self.env['kg.grn'].search([('id', '=', self.name.id)])
            self.entry_date = grn.entry_date
            self.entry_type = grn.entry_type
            self.partner_id = grn.partner_id.id
            self.division_id = grn.division_id.id
            self.department_id = grn.department_id.id
            for grn_line in grn.line_ids:
                grn_amend_line.append((0, 0, {
                    "product_id": grn_line.product_id.id,
                    "inward_id": grn_line.inward_id.id,
                    "grn_line_id": grn_line.id,
                }))

        self.line_ids = grn_amend_line
        return {'line_ids': grn_amend_line}

    @api.multi
    def entry_confirm(self):
        """ entry_confirm """
        if self.state == 'draft':
            self.validations()
            self.write({'state': 'confirmed',
                        'confirm_user_id': self.env.user.id,
                        'confirm_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            pass
        return True

    @api.multi
    def entry_approve(self):
        """ entry_approve """
        if self.state == 'confirmed':
            if self.env.user.id in [
                    self.confirm_user_id.id,
                    self.user_id.id] and self.env.user.is_mgmt_group == False:
                raise UserError(
                    ('Approve cannot be done by confirmed/created user!!'))
            self.validations()
            self.write({'state': 'wfa_mgmt',
                        'approved_user_id': self.env.user.id,
                        'approved_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            pass
        return True


    @api.constrains('name')
    def grn_number_varification(self):
        if self.name:
            grn_amend = self.env['kg.grn.amend'].search_count(
                [('name', 'in', self.name.name), ('state', 'not in', ['approved', 'cancel', 'reject'])])
            if 1 < grn_amend:
                raise UserError(
                    ('Duplicate entry. Already same GRN is in amendment progress. Kindly use that entry and process further.'))

    @api.multi
    def entry_mgmt_approve(self):
        """ entry_approve """
        if self.state == 'wfa_mgmt':
            self.validations()
            billing_list = []

            def check_inward_applicable(inward_rec, grn_line):
                inward_source = []
                for inw_rec in inward_rec:
                    inward = self.env['kg.inwardmaster'].search([('id', '=', inw_rec.id), ('state', 'in', [
                                'approved']), ('stock_process', '=', 'applicable'), ('invoice_process', '=', 'applicable')])
                    if grn_line.header_id.entry_type == 'from_gp':
                       inward = self.env['kg.inwardmaster'].search([('id', '=', inw_rec.id), ('state', 'in', [
                                'approved']), ('stock_process', '=', 'applicable')])
                    if inward:
                        inward_source.append(True)
                    else:
                        inward_source.append(False)

                ## Billing Status ###
                if inward_source[1]:
                    billing_list.append('applicable')
                else:
                    billing_list.append('not_applicable')

                if inward_source[0] and inward_source[1]:
                    grn_line.inward_id = grn_amend_line.amend_inward_id.id
                elif not inward_source[0] and not inward_source[1]:
                    grn_line.inward_id = grn_amend_line.amend_inward_id.id
                elif inward_source[0] and not inward_source[1]:  # Ture >>>> False
                    grn_line.inward_id = grn_amend_line.amend_inward_id.id
                    ### QTY Increase ###
                    if self.entry_type in ['from_po']:
                        if grn_line.po_line_id:
                            grn_line.po_line_id.pending_qty = grn_line.po_line_id.pending_qty + grn_line.qty

                            ## MR state change ###
                            if grn_line.po_line_id.indent_line_id.indent_line_id:
                                grn_line.po_line_id.indent_line_id.indent_line_id.state = 'po_released'
                                grn_line.po_line_id.indent_line_id.indent_line_id.grn_ref = False

                    if self.entry_type in ['from_so']:
                        ### SO Qty Incresing ###
                        if grn_line.so_line_id:
                            grn_line.so_line_id.pending_qty = grn_line.so_line_id.pending_qty + grn_line.qty

                            ### MR state change ###
                            if grn_line.so_line_id.header_id.so_from == 'gate_pass':
                                if grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id:
                                    grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id.state = 'so_released'
                                    grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id.grn_ref = False
                                if grn_line.so_line_id.header_id.so_from == 'indent':
                                    grn_line.so_line_id.soindent_line_id.indent_line_id.state = 'so_released'
                                    grn_line.so_line_id.soindent_line_id.indent_line_id.grn_ref = False

                    if self.entry_type in ['from_pi']:
                        if grn_line.pi_line_id:
                            grn_line.pi_line_id.bal_qty = grn_line.pi_line_id.bal_qty + grn_line.qty

                            ### MR status Change ###
                            if grn_line.pi_line_id.indent_line_id:
                                grn_line.pi_line_id.indent_line_id.state = 'pi_progress'
                                grn_line.pi_line_id.indent_line_id.grn_ref = False

                elif not inward_source[0] and inward_source[1]:  # False >>> True
                    grn_line.inward_id = grn_amend_line.amend_inward_id.id
                    ### QTY Decrease ###
                    if self.entry_type in ['from_po']:
                        if grn_line.po_line_id:
                            grn_line.po_line_id.pending_qty = grn_line.po_line_id.pending_qty - grn_line.qty

                        ## MR state change ###
                        if grn_line.po_line_id.indent_line_id.indent_line_id:
                            if grn_line.header_id.state in ['approved']:
                                grn_line.po_line_id.indent_line_id.indent_line_id.state = 'grn_qc'
                            elif grn_line.header_id.state in ['confirmed']:
                                grn_line.po_line_id.indent_line_id.indent_line_id.state = 'grn'
                            grn_line.po_line_id.indent_line_id.indent_line_id.grn_ref = grn_line.header_id.name

                    if self.entry_type in ['from_so']:
                        ### SO Qty Decresing ###
                        if grn_line.so_line_id:
                            grn_line.so_line_id.pending_qty = grn_line.so_line_id.pending_qty - grn_line.qty

                            ### MR state change ###
                            if grn_line.so_line_id.header_id.so_from == 'gate_pass':
                                if grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id:
                                    if grn_line.header_id.state in [
                                            'approved']:
                                        grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id.state = 'grn_qc'
                                    elif grn_line.header_id.state in ['confirmed']:
                                        grn_line.so_line_id.gatepass_line_id.si_line_id.indent_line_id.state = 'grn_qc'
                            if grn_line.so_line_id.header_id.so_from == 'indent':
                                if grn_line.header_id.state in ['approved']:
                                    if grn_line.so_line_id.soindent_line_id:
                                        grn_line.so_line_id.soindent_line_id.indent_line_id.state = 'grn_qc'
                                elif grn_line.header_id.state in ['confirmed']:
                                    if grn_line.so_line_id.soindent_line_id:
                                        grn_line.so_line_id.soindent_line_id.indent_line_id.state = 'grn'
                                if grn_line.so_line_id.soindent_line_id:
                                    grn_line.so_line_id.soindent_line_id.indent_line_id.grn_ref = grn_line.header_id.name

                    if self.entry_type in ['from_pi']:
                        if grn_line.pi_line_id:
                            grn_line.pi_line_id.bal_qty = grn_line.pi_line_id.bal_qty - grn_line.qty

                        ### MR status Change ###
                        if grn_line.pi_line_id.indent_line_id:
                            if grn_line.header_id.state in ['approved']:
                                grn_line.pi_line_id.indent_line_id.state = 'grn_qc'
                            elif grn_line.header_id.state in ['confirmed']:
                                grn_line.pi_line_id.indent_line_id.state = 'grn'
                            grn_line.pi_line_id.indent_line_id.grn_ref = grn_line.header_id.name

            if self.line_ids:
                for grn_amend_line in self.line_ids:
                    if grn_amend_line.inward_id != grn_amend_line.amend_inward_id:
                        if self.entry_type == 'from_mr':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)
                        elif self.entry_type == 'direct':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)
                        elif grn_amend_line.grn_line_id.header_id.entry_type == 'from_gp':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)
                        elif grn_amend_line.grn_line_id.header_id.entry_type == 'from_pi':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)
                        elif grn_amend_line.grn_line_id.header_id.entry_type == 'from_po':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)
                        elif grn_amend_line.grn_line_id.header_id.entry_type == 'from_so':
                            check_inward_applicable(
                                [grn_amend_line.inward_id, grn_amend_line.amend_inward_id], grn_amend_line.grn_line_id)

                    stock_inward = self.env['kg.inwardmaster'].search(
                        [
                            ('id',
                             '=',
                             grn_amend_line.amend_inward_id.id),
                            ('state',
                             'in',
                             ['approved']),
                            ('stock_process',
                             '=',
                             'applicable')])
                    if not stock_inward:
                        stock_rec = self.env['kg.department.issue'].search(
                            [('grn_no', '=', self.name.name), ('state', 'in', ['draft'])])
                        if stock_rec:
                            # stock.unlink()
                            for stock in stock_rec:
                                self.env.cr.execute(
                                    """ delete from kg_department_issue where id = %s """ %
                                    (stock.id))
                    invoice_inward = self.env['kg.inwardmaster'].search(
                        [
                            ('id',
                             '=',
                             grn_amend_line.amend_inward_id.id),
                            ('state',
                             'in',
                             ['approved']),
                            ('invoice_process',
                             '=',
                             'applicable')])
                    if not invoice_inward:
                        invoice = self.env['kg.purchase.invoice'].search(
                            [('grn_no', '=', self.name.name), ('state', 'in', ['draft'])])
                        if invoice:
                            # invoice.unlink()
                            self.env.cr.execute(
                                """ delete from kg_purchase_invoice where id = %s """ %
                                (invoice.id))

            self.name.billing_status = 'applicable' if 'applicable' in billing_list else 'not_applicable'
            if self.name.billing_status == 'not_applicable':
               self.name.state = 'wfa_reference'

            if self.entry_type in ['from_pi', 'from_po', 'from_so']:

                if self.entry_type in ['from_so']:
                    self.env['purchase.order'].po_so_status_change(
                        'so', 0, grn_amend_line.grn_line_id.so_line_id.header_id.id)

                if self.entry_type in ['from_po']:
                    ##### PO Status change ###
                    self.env['purchase.order'].po_so_status_change(
                        'po', grn_amend_line.grn_line_id.po_line_id.header_id.id, 0)

                self.name.auto_issue_process()

                ### Invoice Draft creation ###
                if self.name.state == 'confirmed':  # WFC
                    self.name.inspection_state = 'start'
                elif self.name.state == 'approved' and self.name.grn_type == 'dc_invoice' and self.name.inspection_state == 'completed':  # WFA-WFI
                    self.name.inspection_approval()
        else:
            pass
        self.write({'state': 'approved',
                    'md_ap_rej_user_id': self.env.user.id,
                    'md_ap_rej_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    ### Entry Rejection ###
    @api.multi
    def entry_reject(self):
        """Entry Reject"""
        if self.state in ['wfa_mgmt', 'confirmed']:
            if self.rejected_remark:
               if self.rejected_remark.isspace():
                  raise UserError("Minimum 10 characters are required for reject remarks")
               if " " in self.rejected_remark:
                  rejected_remark = self.rejected_remark.replace(" ","")
                  if len(rejected_remark) < 10:
                     raise UserError("Minimum 10 characters are required for rejected remarks")
               else:
                  if len(self.rejected_remark) < 10:
                    raise UserError(
                        ('Minimum 10 characters is must for reject remarks'))

               self.write({'state': 'reject',
                           'rejected_by': self.env.user.id,
                           'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})

            else:
                raise UserError(
                        ('Rejection remarks is must !! Enter the remarks in Rejection remarks field !!'))
        else:
            pass
        return True

    @api.multi
    def unlink(self):
        """ code_validation """
        for rec in self:
            if rec.state not in ('draft'):
                raise UserError('Warning, you can not delete this entry')
            else:
                models.Model.unlink(rec)
        return True

    @api.multi
    def write(self, vals):
        """ write """
        vals.update({'update_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                     'update_user_id': self.env.user.id})
        return super(KgGrnAmend, self).write(vals)


KgGrnAmend()


class ChGrnAmendLine(models.Model):
    """ Ch GRN Amendment """
    _name = "ch.grn.amend.line"
    _description = "GRN Details"

    header_id = fields.Many2one(
        'kg.grn.amend',
        'GRN Amend',
        ondelete='cascade')
    grn_line_id = fields.Many2one('kg.grn.line', 'GRN Line', store=True)
    product_id = fields.Many2one(
        'product.product', 'Product', readonly=True, domain=[
            ('state', '=', 'approved')])

    inward_id = fields.Many2one(
        'kg.inwardmaster', 'Inward Type', readonly=True, domain=[
            ('active_trans', '!=', False), ('state', '=', 'approved')])

    amend_inward_id = fields.Many2one(
        'kg.inwardmaster', 'Amend Inward Type', domain=[
            ('active_trans', '!=', False), ('state', '=', 'approved')])

    @api.onchange('amend_inward_id')
    def change_amend_inward_id(self):
        if self.amend_inward_id:
            if self.inward_id.id == self.amend_inward_id.id:
               raise UserError(
                        ('Inward type and amend inward type should not be same.'))
               

ChGrnAmendLine()
