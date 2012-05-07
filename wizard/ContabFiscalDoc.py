# -*- encoding: utf-8 -*- 

import time

import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
import tools
def arrot(cr,uid,valore,decimali):
    #import pdb;pdb.set_trace()
    return round(valore,decimali(cr)[1])

class contab_fiscaldoc(osv.osv_memory):
    _name = "contab.fiscaldoc"
    _columns = {
                'to_date_doc': fields.date('Fino A data Documento', required=True),
                'fldtreg':fields.boolean('Data Reg. = Data Doc.', required=True, help = "Se attivo la data registrazione sara uguale alla data documento"),                 
                'date': fields.date('Data Registrazione', required=True),
                
                }
    
    _defaults = {  
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'fldtreg':True,
        }
    

           
    def cont_fiscalfdoc(self,cr,uid,ids,context):
        # Contabilizza i documenti non ancora contabilizzati
        #import pdb;pdb.set_trace()
        if ids:
            param = self.browse(cr,uid,ids)[0]
            cerca = [
                     ('data_documento','<=',param.to_date_doc),
                     ('registrazione','=',None),
                     ('tipo_documento','<>','DT'),
                     ('tipo_operazione','=','C'),
                     ('tipo_azione','=','VE')
                     ]
            ids_docs = self.pool.get('fiscaldoc.header').search(cr,uid,cerca,order='data_documento,name,doc_prog')
            testo_log = """Inizio procedura Contabilizzazione documenti di Vendita """ + time.ctime() + '\n'
            if ids_docs:
                testo_log = """Inizio procedura Contabilizzazione documenti di Vendita """ + time.ctime() + '\n'
                for doc in self.pool.get('fiscaldoc.header').browse(cr,uid,ids_docs):
                    if not doc.tipo_doc.causale_id:
                        testo_log += """Causale Documento  """ +doc.tipo_doc.name +" SENZA CAUSALE CONTABILE " + '\n' + "  Documento "+ doc.name + " NON CONTABILIZZATO "+ '\n'
                    else:
                        scritto = self.scrive_reg(cr, uid, doc,param,context)
                        testo_log += scritto[0] 
                        # TO DO INCASSO CONTESTUALE PER IMPORTO ACCONTO MOVIMENTATO
            else:
                #testo_log = """NON CI SONO DICUMENTI PER I PARAMETRI INDICATI """ + time.ctime() + '\n'
                raise osv.except_osv(_('ERRORE !'), _('NON CI SONO DOCUMENTI PER I PARAMETRI INDICATI '))
                
        testo_log = testo_log + " Operazione Teminata  alle " + time.ctime() + "\n"
        #invia e-mail
        user = self.pool.get('res.users').browse(cr,uid,uid)
        #import pdb;pdb.set_trace()
        if user.user_email:            
         type_ = 'plain'
         tools.email_send('OpenErp@server.it',
                       [user.user_email], # QUA DEVE ESSERCI L'EMAIL DEL CODICE UTENTE DEVI ANCHE ATTIVARE LA MESSAGGISTICA INTERNA DEGLI ESITI
                       'Esito Contabilizzazione Documenti',
                       testo_log,
                       subtype=type_,
                       )

                
            
        
        return   {'type': 'ir.actions.act_window_close'}  
    
    def scrive_reg(self,cr,uid,doc,param,context):
        
        move_obj= self.pool.get('account.move')
        if param.fldtreg:
            data_reg = doc.data_documento
        else:
            data_reg = param.date
        riga_head = {
                     'ref':doc.name,
                     'date':data_reg,
                     'partner_id':doc.partner_id.id,
                     'numero_doc':doc.name,
                     'data_doc':doc.data_documento,
                     'pagamento_id':doc.pagamento_id.id,
                     'causale_id':doc.tipo_doc.causale_id.id,
                     'fiscaldoc_id':doc.id,
                     }
        defa = move_obj.default_get(cr, uid, ['period_id','state','name','company_id'], context=None) 
        riga_head.update(defa)      
        value = move_obj.onchange_causale_id(cr,uid,[],doc.tipo_doc.causale_id.id,defa.get('period_id',False),data_reg,context)
        value['value']['ref']= doc.name+' '+  value['value']['ref']
        #riga_head['name']= value['value']['ref']
        #import pdb;pdb.set_trace()
        riga_head.update(value['value'])
        
        id_reg = move_obj.create(cr,uid,riga_head,context)
        if id_reg:
            
            move_head= move_obj.browse(cr,uid,id_reg)             
            scritto = self.scrive_account_move_line(cr, uid,move_head,doc, context)
            if scritto[1]:
               #import pdb;pdb.set_trace()
               notok= move_obj.button_validate(cr,uid,[id_reg],context)
               if notok==False:
                    ok = self.pool.get('fiscaldoc.header').write(cr,uid,[doc.id],{'registrazione':id_reg})              
                    scritto[0] = scritto[0]+ "  Documento "+ doc.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +'\n'
               else:
                     #import pdb;pdb.set_trace()
                     scritto[0] =  scritto[0]+ "  Documento "+ doc.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +' MA NON VALIDATO \n'
        return scritto
    

    
    def scrive_account_move_line(self,cr, uid,move_head,doc, context):
        
        def default_riga(move_head,doc):
            riga = {
                    'name': move_head.ref,
                    'period_id':move_head.period_id.id,
                    'journal_id':move_head.journal_id.id,
                    'partner_id':doc.partner_id.id,
                    'move_id':move_head.id,
                    'date':move_head.date,
                    'ref':move_head.ref,
                    'causale_id':move_head.causale_id.id,                    
                    }
            return riga
        
        def cerca_controp(riga_doc):
            conto_id = False
            if riga_doc.contropartita:
                conto_id= riga_doc.contropartita.id
            elif riga_doc.product_id.categ_id.property_account_income_categ:
                conto_id = riga_doc.product_id.categ_id.property_account_income_categ.id
            return conto_id
        
        
        testo_log = """ """
        flag_scritto= True
        # ora cicla sulle righe documento, ma deve riportarsi gli sconti di testata.
        # spese diverse 
        ids_controp = self.pool.get('controp.costi.ricavi').search(cr,uid,[])
        if ids_controp:
            controp_obj= self.pool.get('controp.costi.ricavi').browse(cr,uid,ids_controp[0])
        else:
            raise osv.except_osv(_('ERRORE !'), _('NON SONO DEFINITE LE CONTROPARTITE COSTI E RICAVI '))
            flag_scritto= False
        if doc.spese_imballo:
                     riga = default_riga(move_head,doc)
                     if doc.tipo_documento=="NC":
                         segno = "DA"
                     else:
                        segno = "AV"       
                     if segno=="DA":
                        #segno dare
                        riga['credit']=0
                        riga['debit']=doc.spese_imballo     
                     else:
                        #segno dare
                        riga['credit']=doc.spese_imballo     
                        riga['debit']=0
                     riga['account_id']= controp_obj.conto_v_sp_imballo.id
                     #import pdb;pdb.set_trace()
                     id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA IMBALLO
                     if not id_riga:
                         flag_scritto= False
            
        if doc.spese_incasso:
                     riga = default_riga(move_head,doc)
                     if doc.tipo_documento=="NC":
                         segno = "DA"
                     else:
                        segno = "AV"       
                     if segno=="DA":
                        #segno dare
                        riga['credit']=0
                        riga['debit']=doc.spese_incasso     
                     else:
                        #segno dare
                        riga['credit']=doc.spese_incasso     
                        riga['debit']=0
                     riga['account_id']= controp_obj.conto_v_sp_incasso.id
                   #  import pdb;pdb.set_trace()
                     id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA INCASSO
                     if not id_riga:
                         flag_scritto= False
                         
                         
        if doc.spese_trasporto:
                     riga = default_riga(move_head,doc)
                     if doc.tipo_documento=="NC":
                         segno = "DA"
                     else:
                        segno = "AV"       
                     if segno=="DA":
                        #segno dare
                        riga['credit']=0
                        riga['debit']=doc.spese_trasporto     
                     else:
                        #segno dare
                        riga['credit']=doc.spese_trasporto     
                        riga['debit']=0
                     riga['account_id']= controp_obj.conto_v_sp_trasporto.id
         #            import pdb;pdb.set_trace()
                     id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA TRASPORTO
                     if not id_riga:
                         flag_scritto= False
#        if flag_scritto:
#             testo_log += "  Documento "+ doc.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_obj.name +'\n'
        riga = default_riga(move_head,doc)
        riga['pagamento_id']=doc.pagamento_id.id
        righe={}
        for riga_art in doc.righe_articoli:
                 if doc.sconto_partner or doc.sconto_pagamento:
                    netto = riga_art.totale_riga
                    if doc.sconto_partner:
                        netto = netto-(netto*doc.sconto_partner/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    if doc.sconto_pagamento:
                        netto = netto-(netto*doc.sconto_pagamento/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                 else:
                    netto = riga_art.totale_riga
                 conto = cerca_controp(riga_art)
                 if not conto:
                    testo_log += "  Documento "+ doc.name + " riga "+ riga_art.product_id.default_code+ ' senza contropartita ricavi '+'DOCUMENTO NON CONTABILIZZATO \n'
                    flag_scritto= False
                 else:
                    if netto==0:
                       pass
                    else:
                     riga= righe.get(conto,False)
                     if not riga:
                        riga = default_riga(move_head,doc)
                        riga['credit']=0
                        riga['debit']=0
                        
                     if doc.tipo_documento=="NC":
                         segno = "DA"
                     else:
                        segno = "AV"       
                     if segno=="DA":
                        #segno dare
                        riga['credit']+=0
                        riga['debit']+=netto     
                     else:
                        #segno dare
                        riga['credit']+=netto     
                        riga['debit']+=0
                     riga['account_id']= conto
                     #import pdb;pdb.set_trace()
                     righe[conto]=riga
        if righe:
            for riga in righe.values():
                id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA RICAVO
                if not id_riga:
                         flag_scritto= False
        #cicla sulle righe iva adesso e scrive le stesse
        for riga_iva in doc.righe_totali_iva:
            riga = default_riga(move_head,doc)
            riga['pagamento_id']=doc.pagamento_id.id
            segno = move_head.causale_id.segno_conto_iva
            conto = move_head.causale_id.conto_iva.id
            riga['account_id']=conto
            riga['imponibile']=riga_iva.imponibile
            riga['account_tax_id']=riga_iva.codice_iva.id
            if segno=="DA":
             #segno dare
             riga['credit']=0
             riga['debit']=riga_iva.imposta
            else:
             #segno dare
             riga['credit']=riga_iva.imposta       
             riga['debit']=0
            # import pdb;pdb.set_trace()
            id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA IVA
            if not id_riga:
                 flag_scritto= False
        # inizia con lo scrivere i dati del cliente
        riga = default_riga(move_head,doc)
        if doc.tipo_documento=="NC":
            segno = "AV"
        else:
            segno = "DA"       
        if segno=="DA":
            #segno dare
            riga['credit']=0
            riga['debit']=doc.totale_documento       
        else:
            #segno dare
            riga['credit']=doc.totale_documento       
            riga['debit']=0
        riga['account_id']= doc.partner_id.property_account_receivable.id
        riga['totdocumento']=doc.totale_documento
        riga['pagamento_id']=doc.pagamento_id.id
       # import pdb;pdb.set_trace()
        id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA CLIENTE
        if not id_riga:
             flag_scritto= False
        #cicla sulle righe iva adesso e scrive le stesse
            
            
        
        
        
        
        
        return [testo_log,flag_scritto]
        
contab_fiscaldoc()




