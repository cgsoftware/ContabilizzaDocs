# -*- encoding: utf-8 -*-
import xmlrpclib
import csv
import sys
import time

# Dati per la connessione all'istanza OpenERP
user = 'admin'
pwd = 'skipper181'
dbname = 'sierp'

# Connessione XMLRPC per autenticazione
sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/common')
uid = sock.login(dbname ,user ,pwd)

# Creazione del proxy XMLRPC
sock = xmlrpclib.ServerProxy('http:/localhost:8069/xmlrpc/object')

# Creazione della lista di records
# lines = csv.reader(open(sys.argv[1],'rb'),delimiter=";")
spamWriter = csv.writer(open('log.csv', 'wb'), delimiter=',')
testo_log = "Inizio procedura di Riallineamento Scadenze "+time.ctime()+'\n'
spamWriter.writerow([testo_log])
counter = 0



cerca = [('scadenza_id','=',None)]
lines_scad =  sock.execute(dbname, uid, pwd, 'effetti.scadenze', 'search', cerca)
if lines_scad:
   #import pdb;pdb.set_trace()
   for line in lines_doc:
     fields = ['numero_doc']
     results = sock.execute(dbname, uid, pwd, 'effetti.scadenze', 'read', [line], fields)
     if results:
         cerca_doc = [('name','=',results[line]['numero_doc'])]
         docs_id =  sock.execute(dbname, uid, pwd, 'fiscaldoc.header', 'search', cerca)
     if not results:
             print 'cancella ', line
             results = sock.execute(dbname, uid, pwd, 'stock.warehouse.orderpoint', 'unlink', [line])
     else:
          print results,line   




testo_log = "Fine  procedura di aggiornamento/inseriti ordini di produzione "+ repr(counter)+"  "+ time.ctime()+'\n'
spamWriter.writerow([testo_log])


