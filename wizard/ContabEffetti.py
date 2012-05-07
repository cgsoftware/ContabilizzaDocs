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

class contab_effetti(osv.osv_memory):
    _name = "contab.effetti"
    _columns = {
                'to_date_doc': fields.date('Fino A data Documento', required=True),
                'fldtreg':fields.boolean('Data Reg. = Data Doc.', required=True, help = "Se attivo la data registrazione sara uguale alla data documento"),                 
                'date': fields.date('Data Registrazione', required=True),
                'causale_id': fields.many2one('causcont', 'Causale', required=True, select=True),  
                'account_eff_id': fields.many2one('account.account', 'Conto Effetti', required=True, ondelete="cascade", domain=[('type','<>','view'), ('type', '<>', 'closed')]),              
                }
    
    _defaults = {  
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'fldtreg':True,
        }
    

           
    def cont_effetti(self,cr,uid,ids,context):
        # Contabilizza effetti ancora contabilizzati
        #import pdb;pdb.set_trace()
        if ids:
            param = self.browse(cr,uid,ids)[0]
            cerca = [
                     ('data_documento','<=',param.to_date_doc),
                     ('registrazione','=',None),
                     ]
            ids_docs = self.pool.get('effetti.scadenze').search(cr,uid,cerca,order='name,data_documento,numero_doc')
            testo_log = """Inizio procedura Contabilizzazione Effetti """ + time.ctime() + '\n'
            if ids_docs:
                testo_log = """Inizio procedura Contabilizzazione Effetti """ + time.ctime() + '\n'
                ids_eff=[]
                for rsca in self.pool.get('effetti.scadenze').browse(cr,uid,ids_docs):
                    if rsca.name.id in ids_eff:
                        pass
                    else:
                        ids_eff.append(rsca.name.id)
                if not ids_eff:
                        raise osv.except_osv(_('ERRORE !'), _('NON CI SONO DOCUMENTI PER I PARAMETRI INDICATI '))
                        # testo_log += """Causale Documento  """ +doc.tipo_doc.name +" SENZA CAUSALE CONTABILE " + '\n' + "  Documento "+ doc.name + " NON CONTABILIZZATO "+ '\n'
                else:
                        for doc in self.pool.get('effetti').browse(cr,uid,ids_eff):
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
                       'Esito Contabilizzazione Effetti',
                       testo_log,
                       subtype=type_,
                       )

                
            
        
        return   {'type': 'ir.actions.act_window_close'}  
    
    def scrive_reg(self,cr,uid,effetto,param,context):
        move_obj= self.pool.get('account.move')
        scritto=[]
        if effetto.righe_scadenze:
            dati_scad ={'scad_doc_id':[],'datadoc':[],'numdoc':''}
            for scad in effetto.righe_scadenze:
                dati_scad['datadoc'].append(scad.data_documento)
                dati_scad['scad_doc_id'].append(scad.scadenza_id)
                dati_scad['numdoc'] +=' '+scad.numero_doc
            #import pdb;pdb.set_trace()
            if len(dati_scad['datadoc'])>0:
                if param.fldtreg:
                     data_reg = max(dati_scad['datadoc'])
                else:
                     data_reg = param.date
                riga_head = {
                                  'date':data_reg,
                                  'partner_id':effetto.cliente_id.id,
                                  'numero_doc':False,
                                  'data_doc':False,
                                  'pagamento_id':False,
                                  'causale_id':param.causale_id.id,
                                  'effetto_id':effetto.id,
                                  }
                defa = move_obj.default_get(cr, uid, ['period_id','state','name','company_id'], context=None) 
                riga_head.update(defa)      
                value = move_obj.onchange_causale_id(cr,uid,[],param.causale_id.id,defa.get('period_id',False),data_reg,context)
                data_sc = effetto.data_scadenza[-2:]+effetto.data_scadenza[4:8]+effetto.data_scadenza[:4]
                value['value']['ref']= 'Scadenza del  '+data_sc+ ' doc. '+ dati_scad['numdoc']
                riga_head.update(value['value'])  
                id_reg = move_obj.create(cr,uid,riga_head,context)
                if id_reg:            
                         move_head= move_obj.browse(cr,uid,id_reg)             
                         scritto = self.scrive_account_move_line(cr, uid,move_head,effetto,dati_scad,param,context)
                         if scritto[1]:
                             #import pdb;pdb.set_trace()
                             notok= move_obj.button_validate(cr,uid,[id_reg],context)
                             if notok==False:
                                 ok = self.pool.get('effetti').write(cr,uid,[effetto.id],{'registrazione':id_reg})  
                                 for scad in effetto.righe_scadenze:
                                     ok= self.pool.get('effetti.scadenze').write(cr,uid,[scad.id],{'registrazione':id_reg})
                                 scritto[0] = scritto[0]+ "  Effetto  "+ effetto.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +'\n'
                             else:
                                 #import pdb;pdb.set_trace()
                                 scritto[0] =  scritto[0]+ "  Effetto  "+ effetto.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +' MA NON VALIDATO \n'
        return scritto



    
    def scrive_account_move_line(self,cr, uid,move_head,doc,dati_scad,param, context):
        
        def default_riga(move_head,doc):
            riga = {
                    'name': move_head.ref,
                    'period_id':move_head.period_id.id,
                    'journal_id':move_head.journal_id.id,
                    'partner_id':doc.cliente_id.id,
                    'move_id':move_head.id,
                    'date':move_head.date,
                    'ref':move_head.ref,
                    'causale_id':move_head.causale_id.id,                    
                    }
            return riga        
        
        
        testo_log = """ """
        flag_scritto= True
        # inizia con lo scrivere i dati del cliente
        riga = default_riga(move_head,doc)
        segno = "AV"
        if segno=="DA":
            #segno dare
            riga['credit']=0
            riga['debit']=doc.importo_effetto   
        else:
            #segno dare
            riga['credit']=doc.importo_effetto       
            riga['debit']=0
        riga['account_id']= doc.cliente_id.property_account_receivable.id
        riga['totdocumento']=doc.importo_effetto
        riga['pagamento_id']=False #doc.pagamento_id.id
       # import pdb;pdb.set_trace()
        id_riga_cli = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA CLIENTE
        if not id_riga_cli:
             flag_scritto= False
        
        # inizia con lo scrivere i dati del cliente
        riga = default_riga(move_head,doc)
        segno = "DA"
        if segno=="DA":
            #segno dare
            riga['credit']=0
            riga['debit']=doc.importo_effetto   
        else:
            #segno dare
            riga['credit']=doc.importo_effetto       
            riga['debit']=0
        riga['account_id']= param.account_eff_id.id
        riga['totdocumento']=doc.importo_effetto
        riga['pagamento_id']=False #doc.pagamento_id.id
       # import pdb;pdb.set_trace()
        id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA Contropartita Effetti
        if not id_riga:
             flag_scritto= False
        # Cerca di chiudere la partita se esiste
        if flag_scritto :
            #import pdb;pdb.set_trace()
            for effetto_scad in doc.righe_scadenze:
                if effetto_scad.scadenza_id:
                    # è certamente agganciato un documento di vendita sulla scadenza, non so se esiste la regisatrazione di prima nota
                    cerca = [('fiscaldoc_id','=',effetto_scad.scadenza_id.name.id)]
                    id_testa_doc = self.pool.get('account.move').search(cr,uid,cerca)
                    if id_testa_doc: # il documento è contabilizzato
                        PntObjBrw = self.pool.get('account.move').browse(cr,uid,id_testa_doc)[0]                        
                        for move_line in PntObjBrw.line_id:
                          #if doc.cliente_id.property_account_receivable.id == move_line.account_id.id:
                            #import pdb;pdb.set_trace()  
                            if move_line.partita_id:                              
                               #è la riga di apertura partita
                                #import pdb;pdb.set_trace()
                                partita =  move_line.partita_id
                                for part_scad in partita.par_scadenze:
                                    if part_scad.data_scadenza==doc.data_scadenza:
                                        # trovata una data scadenza uguale nella partita, quindi devo scrivere un record che salda la scadenza
                                        #import pdb;pdb.set_trace()
                                        riga_sald = {
                                                     'name': part_scad.id,
                                                     'registrazione': id_riga_cli,
                                                     'saldo': part_scad.da_saldare,                                                                        
                                                     }
                                        id_saldo = self.pool.get('account.partite_saldi').create(cr,uid,riga_sald)
                    else:
                        testo_log += " Il Documento "+ effetto_scad.scadenza_id.name.name + " non sembra essere Contabilizzata"
        return [testo_log,flag_scritto]
    
    def allinea_scad(self,cr,uid,ids,context):
        cerca = [('scadenza_id','=',None)]
        ids_scads = self.pool.get('effetti.scadenze').search(cr,uid,cerca)
        if ids_scads:
            for scad in self.pool.get('effetti.scadenze').browse(cr,uid,ids_scads):               
                cerca = [('name','=' ,scad.numero_doc)]
                id_doc=self.pool.get('fiscaldoc.header').search(cr,uid,cerca)
                if id_doc:
                    for docu in self.pool.get('fiscaldoc.header').browse(cr,uid,id_doc):
                        for sca_doc in docu.righe_scadenze:
                            if scad.name.data_scadenza == sca_doc.data_scadenza:
                                ok = self.pool.get('effetti.scadenze').write(cr,uid,[scad.id],{'scadenza_id':sca_doc.id})
        
    
        return   {'type': 'ir.actions.act_window_close'}          
contab_effetti()




