from telegram import ChatAction,InlineQueryResultArticle,InlineQueryResultPhoto, ParseMode, InputTextMessageContent, Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler,Updater, InlineQueryHandler, CommandHandler, CallbackContext,MessageHandler,Filters
from telegram.utils.helpers import escape_markdown
from uuid import uuid4
import MoodleClient
import os
import random
import time
import requests
import config
import mediafire
import googledrive
from mega import Mega
import zipfile
import youtube_dl
import vdirect
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger("telegram").setLevel(logging.WARNING)


def sendHtml(update,html):
    return update.message.reply_text(html, parse_mode=ParseMode.HTML)

def editHtml(message,html):
    return message.edit_text(html, parse_mode=ParseMode.HTML)

def get_file_size(file):
    file_size = os.stat(file)
    return file_size.st_size

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def req_file_size(req):
    try:
        return int(req.headers['content-length'])
    except:
        return 0

def get_url_file_name(url,req):
    try:
        if "Content-Disposition" in req.headers.keys():
            return str(re.findall("filename=(.+)", req.headers["Content-Disposition"])[0])
        else:
            import urllib
            urlfix = urllib.parse.unquote(url,encoding='utf-8', errors='replace')
            tokens = str(urlfix).split('/');
            return tokens[len(tokens)-1]
    except:
        import urllib
        urlfix = urllib.parse.unquote(url,encoding='utf-8', errors='replace')
        tokens = str(urlfix).split('/');
        return tokens[len(tokens)-1]
    return ''


def text_progres(index,max):
	try:
		if max<1:
			max += 1
		porcent = index / max
		porcent *= 100
		porcent = round(porcent)
		make_text = ''
		index_make = 1
		make_text += '\n['
		while(index_make<21):
			if porcent >= index_make * 5: make_text+='█'
			else: make_text+='░'
			index_make+=1
		make_text += ']\n'
		return make_text
	except Exception as ex:
			return ''


def procesUploadFile(update,message,file_name,file_size):
               infotext = '<b>⚠ Información ⚠ </b>\n'
               infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
               infotext+= '<b>🗂Tamaño : '+sizeof_fmt(file_size)+'</b>\n'
               infotext+= '<b>📊Estado : ⌛ Procesando Archivo ⌛...</b>\n'
               editHtml(message,infotext)

               evidence = {}
               evname = str(file_name).split('.')[0]
               client = MoodleClient.MoodleClient(config.CREDENTIALS['username'],config.CREDENTIALS['password'])
               loged = client.login()
               if loged:
                   evidence = client.createEvidence(evname)
               else:
                   infotext = '<b>❌ Error con el servidor ❌ </b>\n'
                   infotext+= '<b>❌ Caído ❌ </b>\n'
                   editHtml(message,infotext)

               maxsize = 1024 * 1024 * config.MAX_ZIP_SIZE
               itemid = None
               if file_size > maxsize:
                    mult_file =  zipfile.MultiFile(file_name+'.7z',maxsize)
                    zip = zipfile.ZipFile(mult_file,  mode='w', compression=zipfile.ZIP_DEFLATED)
                    zip.write(file_name)
                    zip.close()
                    mult_file.close()

                    for part in zipfile.files:
                            try:
                                part_size = get_file_size(part)
                                itemid = uploadToCloud(update,message,part,part_size,evidence,itemid)
                            except:pass
               else:
                   itemid = uploadToCloud(update,message,file_name,file_size,evidence,itemid)


               if len(zipfile.files) > 1:
                   for part in zipfile.files:
                        os.remove(part)
               else:
                   pass


def uploadToCloud(update,message,file_name,file_size,evidence,itemid=None):
                    infotext = '<b>⚠ Información ⚠ </b>\n'
                    infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
                    infotext+= '<b>🗂Tamaño : '+sizeof_fmt(file_size)+'</b>\n'
                    infotext+= '<b>📊Estado : ⏫ Subiendo a la Nube ☁...</b>\n'
                    editHtml(message,infotext)

                    client = MoodleClient.MoodleClient(config.CREDENTIALS['username'],config.CREDENTIALS['password'])
                    loged = client.login()
                    if loged:
                        fileid = client.upload_save(file_name,evidence,itemid)
                        infotext = '<b>✅ Proceso Finalizado! ✅</b>'
                        editHtml(message,infotext)
                        return fileid
                    else:
                        infotext = '<b>⚠ Error ddl ⚠ </b>\n'
                        infotext+= '<b>❌ Verifique sus Credenciales ❌</b>\n'
                        editHtml(message,infotext)
                    return None

def ddl(update,url,session=None,filename='',message=None):
    try:
            if message == None:
                message = sendHtml(update,'<b>⏬Extrayendo Infomación⏳...</b>')
            req = ''

            if session:
                req = session.get(url, stream = True,allow_redirects=True)
            else:
                req = requests.get(url, stream = True,allow_redirects=True)

            if req.status_code == 200:
                file_size = req_file_size(req)
                file_name = get_url_file_name(url,req)
                if filename!='':
                    file_name = filename

                infotext = '<b>⚠ Información ⚠ </b>\n'
                infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
                infotext+= '<b>🗂Tamaño : '+sizeof_fmt(file_size)+'</b>\n'
                infotext+= '<b>📊Estado : 📥 Preparando Descarga 📥...</b>\n'
                editHtml(message,infotext)

                file_wr = open(file_name,'wb')
                chunk_por = 0
                chunkrandom = 100
                
                total = file_size

                time_start = time.time()
                time_total = 0
                size_per_second = 0

                for chunk in req.iter_content(chunk_size = 1024):
                    chunk_por += len(chunk)
                    size_per_second+=len(chunk);

                    tcurrent = time.time() - time_start
                    time_total += tcurrent
                    time_start = time.time()

                    file_wr.write(chunk)

                    if time_total>=1:
                        progres_text = text_progres(chunk_por,total)
                        infotext = '<b>⚠ Información ⚠ </b>\n'
                        infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
                        infotext+= '<b>📊Estado : ⏬ Descargando 📥...</b>\n'
                        infotext+= '<b>'+'🔋Progreso:\n'+str(progres_text)+'\nDescargado: '+str(round(float(chunk_por) / 1024 / 1024, 2))+' MB\nTotal: ' +str(round(total / 1024 / 1024, 2))+ ' MB'+'</b>\n'
                        infotext+= '<b>'+'⚡Velocidad: '+sizeof_fmt(size_per_second)+' /s</b>\n'
                        try:
                            editHtml(message,infotext)
                        except:pass
                        time_total = 0
                        size_per_second = 0

                file_wr.close()

                procesUploadFile(update,message,file_name,file_size)
               
                os.unlink(file_name)
    except Exception as ex:
                print(str(ex))
                infotext = '<b>⚠ Error ddl ⚠ </b>\n'
                infotext+= '<b>'+str(ex)+'</b>\n'
                editHtml(message,infotext)

def sendFiles(update,account):
    message = sendHtml(update,'<b>⏬Extrayendo Archivos⏳...</b>')
    moodle = MoodleClient.MoodleClient(account['username'],account['password'])
    loged = moodle.login()
    if loged:
        list = moodle.getEvidences()
        infotext = '<b>🗂Archivos : ('+str(len(list))+')</b>\n\n'
        i = 0
        for item in list:
            txt = open(item['name']+'.txt','w')
            infotext += '<b>/del_'+str(i)+'</b>\n'
            infotext += '<b>/vdirect_'+str(i)+'</b>\n'
            infotext += '<b>'+item['name']+':</b>\n'
            for file in item['files']:
                txt.write(file['url']) #+'&token='+moodle.userdata['token']+'\n')
                infotext += '<a href="'+file['url']+'">\t'+file['name']+'</a>\n'
            txt.close()
            infotext+='\n'
            i+=1
            file_name = item['name']+'.txt'
            files = open(file_name,'r')
            update.message.reply_document(files)
            os.unlink(file_name)
        editHtml(message,infotext)
        

    else:
        infotext = '<b>⚠ Error ⚠ </b>\n'
        infotext+= '<b>❌ Verifique sus Credenciales ❌</b>\n'
        editHtml(message,infotext)

def delFile(update,index):
    message = sendHtml(update,'<b>⏬Extrayendo Archivos⏳...</b>')
    client = MoodleClient.MoodleClient(config.CREDENTIALS['username'],config.CREDENTIALS['password'])
    loged = client.login()
    if loged:
        list = client.getEvidences()
        evid = list[index]
        editHtml(message,'<b>🗑 Eliminando 🗑...'+evid['name']+'</b>')
        client.deleteEvidence(evid)
        editHtml(message,'<b>✅ Accion Completada! ✅</b>')
    else:
        infotext = '<b>⚠ Error ⚠ </b>\n'
        infotext+= '<b>❌ Verifique sus Credenciales ❌</b>\n'
        editHtml(message,infotext)

def delFiles(update):
    message = sendHtml(update,'<b>⏬Extrayendo Archivos⏳...</b>')
    client = MoodleClient.MoodleClient(config.CREDENTIALS['username'],config.CREDENTIALS['password'])
    loged = client.login()
    if loged:
        files = client.getFiles()
        for ff in files:
            fullname = get_url_file_name(ff['url'],'').split('?')[0]
            editHtml(message,'<b>🗑 Eliminando 🗑...'+fullname+'...</b>')
            client.delteFile(ff['fullname'])
            editHtml(message,'<b>'+fullname+' 🗑 Eliminado! ✅</b>')
    else:
        infotext = '<b>⚠ Error ⚠ </b>\n'
        infotext+= '<b>❌ Verifique sus Credenciales ❌</b>\n'
        editHtml(message,infotext)

def megadl(update,megaurl):
    message = sendHtml(update,'<b>⏬Extrayendo Infomación⏳...</b>')
    try:
                
                megadl = Mega({'verbose': True})
                megadl.login()
                info = megadl.get_public_url_info(megaurl)
                file_name = info['name']
                file_size = info['size']
                size =  sizeof_fmt(file_size)

                infotext = '<b>⚠ Información ⚠ </b>\n'
                infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
                infotext+= '<b>🗂Tamaño : '+size+'</b>\n'
                infotext+= '<b>📊Estado : ⏬ Descargando 📥...</b>\n'
                editHtml(message,infotext)

                megadl.download_url(megaurl,dest_filename=file_name)

                infotext = '<b>⚠ Información ⚠ </b>\n'
                infotext+= '<b>📃Nombre : '+file_name+'</b>\n'
                infotext+= '<b>🗂Tamaño : '+sizeof_fmt(file_size)+'</b>\n'
                infotext+= '<b>📊Estado : 📥 Preparando Descarga 📥...</b>\n'
                editHtml(message,infotext)

                procesUploadFile(update,message,file_name,file_size)
                
                os.unlink(file_name)
    except Exception as ex:
            infotext = '<b>⚠ Error megadl ⚠ </b>\n'
            infotext+= '<b>'+str(ex)+'</b>\n'
            editHtml(message,infotext)


def get_youtube_info(url):
    yt_opt = {
        'no_warnings':True,
        'ignoreerrors':True,
        'restrict_filenames':True,
        'dumpsinglejson':True,
        'format':'best[protocol=https]/best[protocol=http]/bestvideo[protocol=https]/bestvideo[protocol=http]'
              }
    ydl = youtube_dl.YoutubeDL(yt_opt)
    with ydl:
        result = ydl.extract_info(
            url,
            download=False # We just want to extract the info
        )
    return result

def filter_formats(formats):
    filter = []
    for f in formats:
        #if '(DASH video)' in f['format']: continue
        #if f['ext'] == 'mp4':
            if f['filesize']:
                 filter.append(f)
    return filter


def process_msg(update,context):
    if update.message.chat.username in config.ACCES_USERS:
        msg = update.message.text
        zipfile.files.clear()
        if '/start' in msg:
            reply_text = '<b>📲 Bienvenido a  ☁ Cloudload ❄ </b>\n'
            reply_text+= '<b>🤖 Tu Bot Personal de Descargas Gratuitas</b>\n\n'
            reply_text+= '<b>👨‍💻 Comandos:</b>\n'
            reply_text+= '<b>/files - Muestra la lista de archivos descargados</b>\n'
            reply_text+= '<b>/del (index) - Borra el archivo index de la lista</b>\n'
            reply_text+= '<b>/size (Tamaño) - Configura el tamaño de las partes ZIP</b>\n\n'
            reply_text+= '<b>Soporte (Url):</b>\n'
            reply_text+= '<b>#mega #mediafire #googlerive #directurl</b>\n'
            sendHtml(update,reply_text)
        elif '/vdirect' in msg:
                index = (int)(str(msg).split('_')[1])
                client = MoodleClient.MoodleClient(config.CREDENTIALS['username'],config.CREDENTIALS['password'])
                loged = client.login()
                if loged:
                    list = client.getEvidences()
                    evid = list[index]
                    txt = open(evid['name']+'.txt','w')
                    for f in evid['files']:
                        vdirecturl = vdirect.generate(f['url'],client.userdata['token'],'8123')
                        txt.write(vdirecturl+'\n')
                    txt.close()
                    txt = open(evid['name']+'.txt','r')
                    update.message.reply_document(txt)
                    txt.close()
                else:
                    infotext = '<b>❌ Error con el servidor ❌ </b>\n'
                    infotext+= '<b>❌ Caído ❌ </b>\n'
                    editHtml(message,infotext)
        elif '/files' in msg:
                sendFiles(update,config.CREDENTIALS)
        elif '/setacc' in msg:
            acc = str(msg).split(' ')[1].split(',')
            config.CREDENTIALS['username'] = acc[0]
            config.CREDENTIALS['password'] = acc[1]
            reply_text = '<b>✅LISTO!✅</b>'
            sendHtml(update,reply_text)
        elif '/size' in msg:
            size = str(msg).replace('/size ','')
            config.MAX_ZIP_SIZE = int(size)
            sendHtml(update,'<b>Tamaño Máximo de ZIP = '+size+'</b>')
        elif '/acc' in msg:
            username = str(msg).replace('/acc ','')
            config.ACCES_USERS.append(username)
            sendHtml(update,'<b>config.ACCES_USERS = '+str(config.ACCES_USERS)+'</b>')
        elif '/ban' in msg:
            username = str(msg).replace('/ban ','')
            config.ACCES_USERS.append(username)
            sendHtml(update,'<b>config.ACCES_USERS = '+str(config.ACCES_USERS)+'</b>')
        elif '/del' in msg:
            try:
                tokens = str(msg).split('_')
                file_index = int(tokens[1])
                delFile(update,file_index)
            except Exception as ex:
                sendHtml(update,'<b>'+str(ex)+'</b>')
        elif 'mediafire' in msg:
            try:
                 url = mediafire.get(msg)
                 ddl(update,url)
            except:
                sendHtml(update,'<b>⛔ Carpeta de Mediafire no Soportada! ⛔</b>')
        elif 'mega.nz' in msg:
             megadl(update,msg)
        elif 'drive.google' in msg:
             fileid = googledrive.parse_url(msg)['file_id']
             url,session = googledrive.getDownloadUrl(fileid)
             ddl(update,url,session)
        elif 'youtube' in msg:
             message = sendHtml(update,'<b>⏬Extrayendo Infomación⏳...</b>')
             videoinfo = get_youtube_info(msg)
             formats = filter_formats(videoinfo['formats'])
             buttons = []
             i = 0
             for f in formats:
                 size = 0
                 try:
                    size = sizeof_fmt(f['filesize'])
                 except:pass
                 ext = ''
                 try:
                    ext = str(f['ext'])
                 except:pass
                 btntext = f['format_note']+' - '+str(size)+' - '+ext
                 buttons.append([InlineKeyboardButton(text=btntext,callback_data='ydl '+msg+' '+str(size))])
                 i+=1
             reply_text = '<a href="'+msg+'">'+videoinfo['title']+'</a>'
             message.edit_text(text=reply_text,parse_mode=ParseMode.HTML,reply_markup=InlineKeyboardMarkup(buttons))

        elif 'http' in msg or 'https' in msg:
            ddl(update,msg)

    pass


def ytdl(update,context):
    upd = update.callback_query
    msg = upd.data

    message = sendHtml(upd,'<b>⏬Extrayendo Infomación⏳...</b>')

    tokens = str(msg).split(' ')
    cmd = tokens[0]
    url = tokens[1]
    size = tokens[2]

    videoinfo = get_youtube_info(url)
    formats = filter_formats(videoinfo['formats'])
    format = ''
    for f in formats:
        fsize = 0
        try:
           fsize = sizeof_fmt(f['filesize'])
        except:pass
        if fsize == size:
            format = f
            break
    file_name = videoinfo['title'] + '.' + format['ext']
    file_size = format['filesize']

    file_name = str(file_name).replace('|','').replace('"','').replace('/','')

    ddl(upd,format['url'],None,file_name,message)


    pass


def main() -> None:
    try:
        updater = Updater(config.BOT_TOKEN)

        dispatcher = updater.dispatcher

        dispatcher.add_handler(CallbackQueryHandler(pattern='ydl',callback=ytdl))
        dispatcher.add_handler(MessageHandler(Filters.text,process_msg))

        updater.start_polling()
        updater.idle()
    except Exception as ex:
        print(str(ex))
        main()


if __name__ == '__main__':
    main()
