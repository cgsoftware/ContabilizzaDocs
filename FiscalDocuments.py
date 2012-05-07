# -*- encoding: utf-8 -*- 


import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _


def arrot(cr,uid,valore,decimali):
    #import pdb;pdb.set_trace()
    return round(valore,decimali(cr)[1])


class controp_costi_ricavi(osv.osv):
    _name = 'controp.costi.ricavi'
    _columns = {
                'name':fields.char("Descrizione",size=64),
                'conto_cassa':fields.many2one('account.account', "Conto Cassa",  required=True, select=False),
                'conto_v_ricacc':fields.many2one('account.account', "Conto Ricavi Accessori",  required=True, select=False),
                'conto_v_sp_incasso':fields.many2one('account.account', "Conto Spese Incasso",  required=True, select=False),
                'conto_v_sp_imballo':fields.many2one('account.account', "Conto Spese Imballo",  required=True, select=False),
                'conto_v_sp_trasporto':fields.many2one('account.account', "Conto Spese Trasoprto",  required=True, select=False),
                'conto_v_omaggi':fields.many2one('account.account', "Conto Omaggi",  required=True, select=False),
                'conto_v_bolli':fields.many2one('account.account', "Conto Bolli",  required=True, select=False),
                'conto_v_ivaomaggi':fields.many2one('account.account', "Conto Iva Omaggi",  required=True, select=False),
                'codice_iva_v_esente':fields.many2one('account.tax', 'Codice Iva Esente', required=True, readonly=False),
                'codice_iva_v_fcampo':fields.many2one('account.tax', 'Codice Iva Fuori Campo', required=True, readonly=False),
                'causale_incasso': fields.many2one('causcont', 'Causale Incasso ', required=True),
                'conto_a_cosacc':fields.many2one('account.account', "Conto Costi Accessori",  required=True, select=False),
                'conto_a_sp_pagamento':fields.many2one('account.account', "Conto Spese Pagamento",  required=True, select=False),
                'conto_a_sp_imballo':fields.many2one('account.account', "Conto Spese Imballo",  required=True, select=False),
                'conto_a_sp_trasporto':fields.many2one('account.account', "Conto Spese Trasoprto",  required=True, select=False),
                'conto_a_omaggi':fields.many2one('account.account', "Conto Omaggi",  required=True, select=False),
                'conto_a_bolli':fields.many2one('account.account', "Conto Bolli",  required=True, select=False),
                'conto_a_ivaomaggi':fields.many2one('account.account', "Conto Iva Omaggi",  required=True, select=False),
                'causale_pagamento': fields.many2one('causcont', 'Causale Pagamento ', required=True),
                'codice_iva_a_esente':fields.many2one('account.tax', 'Codice Iva Esente', required=True, readonly=False),
                'codice_iva_a_fcampo':fields.many2one('account.tax', 'Codice Iva Fuori Campo', required=True, readonly=False),                

                    }

controp_costi_ricavi()

class fiscaldoc_causalidoc(osv.osv):
   _inherit = "fiscaldoc.causalidoc"
   _columns = {
               'causale_id': fields.many2one('causcont', 'Causale Contabile ', required=False),
                   }
fiscaldoc_causalidoc()

class FiscalDocHeader(osv.osv):
   _inherit = "fiscaldoc.header"
   _columns ={
             'registrazione': fields.many2one('account.move', 'Registrazione di Prima Nota'),
             'tipo_documento': fields.related('tipo_doc', 'tipo_documento', string='Tipo Documento', type='char', relation='fiscaldoc.causalidoc'),
             'flag_contabile': fields.related('tipo_doc', 'flag_contabile', string='Documento Contabilizzabile', type='boolean', relation='fiscaldoc.causalidoc'),
             'tipo_documento': fields.related('tipo_doc', 'tipo_documento', string='Tipo Documento', type='char', relation='fiscaldoc.causalidoc'),
             'tipo_operazione': fields.related('tipo_doc', 'tipo_operazione', string='Tipo Operazione', type='char', relation='fiscaldoc.causalidoc'),
             'tipo_azione': fields.related('tipo_doc', 'tipo_azione', string='Tipo Azione', type='char', relation='fiscaldoc.causalidoc'),
             }
    

FiscalDocHeader()


class EffettiScadenze(osv.osv):
    _inherit = "effetti.scadenze"
    _columns ={
            'registrazione': fields.many2one('account.move', 'Registrazione di Prima Nota'),
             }

EffettiScadenze()



class EffettiHeader(osv.osv):
    _inherit = "effetti"
    _columns ={
             'registrazione': fields.many2one('account.move', 'Registrazione di Prima Nota'),
    }

EffettiHeader()

class account_move(osv.osv):
    _inherit = "account.move"
    _columns={
              'fiscaldoc_id': fields.many2one('fiscaldoc.header', 'Documento di Riferimento'),
              'effetto_id': fields.many2one('effetti', 'Eventuale riba di Riferimento'),
              }
    
    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}    
        result = False  
        if ids:
            for riga_reg in self.browse(cr,uid,ids):
                if riga_reg.fiscaldoc_id:
                    ok = self.pool.get('fiscaldoc.header').write(cr,uid,[riga_reg.fiscaldoc_id.id],{'registrazione':False})  
                if riga_reg.effetto_id:
                    ok = self.pool.get('effetti').write(cr,uid,[riga_reg.effetto_id.id],{'registrazione':False})  
                    ids_sca = self.pool.get('effetti.scadenze').search(cr,uid,[('registrazione','in',ids)])
                    if ids_sca:
                          ok = self.pool.get('effetti.scadenze').write(cr,uid,ids_sca,{'registrazione':False})
        result = super(account_move,self).unlink(cr,uid,ids,context)
        return result
    
    
account_move()