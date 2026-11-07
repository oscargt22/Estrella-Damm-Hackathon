"""Panel local Typeform. Solo biblioteca estándar Python; sin dependencias externas."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlencode
import json, os, re, ssl

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / 'objetivos.json'


def token():
    t = os.getenv('TYPEFORM_TOKEN', '').strip()
    if t: return t
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith('TYPEFORM_TOKEN='):
                return line.split('=',1)[1].strip().strip('"\'')
    return ''


def targets():
    try:
        obj = json.loads(SETTINGS.read_text(encoding='utf-8'))
        return {str(k): int(v) for k,v in obj.items() if isinstance(v,int) and v>0}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def typeform(path, *, base='https://api.typeform.com', method='GET', data=None):
    url = base.rstrip('/') + path
    headers={'Authorization':'Bearer '+token(), 'Accept':'application/json'}
    if data is not None: headers['Content-Type']='application/json'
    req = Request(url, data=json.dumps(data).encode('utf-8') if data is not None else None, headers=headers, method=method)
    try:
        with urlopen(req, timeout=18) as res:
            return json.load(res)
    except HTTPError as e:
        if e.code == 401: raise ValueError('Token rechazado (401). Revisa TYPEFORM_TOKEN.')
        if e.code == 403: raise ValueError('Sin permiso (403). El token necesita forms:read y responses:read.')
        if e.code == 429: raise ValueError('Demasiadas peticiones a Typeform. Inténtalo después.')
        detail = e.read(1200).decode('utf-8','replace')
        try:
            parsed=json.loads(detail)
            detail=parsed.get('description') or parsed.get('message') or parsed.get('code') or ''
        except ValueError: detail=''
        raise ValueError(('Error Typeform (HTTP %d). %s' % (e.code, detail))[:350])
    except (URLError, TimeoutError):
        raise ValueError('No se pudo conectar con Typeform. Revisa Internet.')


def get_forms():
    if not token(): raise ValueError('Falta TYPEFORM_TOKEN en el archivo .env.')
    forms = []
    page = 1
    while page <= 10:
        response = typeform('/forms?' + urlencode({'page_size': 100, 'page': page}))
        items = response.get('items') or []
        forms.extend(items)
        if len(items) < 100: break
        page += 1
    result = []
    counts = targets()
    for f in forms:
        form_id = f.get('id', '')
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', form_id): continue
        try:
            meta = typeform('/forms/' + form_id)
            raw = meta.get('_links', {}).get('responses', '')
            # URL devuelta por Typeform: puede indicar centro de datos europeo.
            parsed = urlparse(raw)
            if parsed.scheme == 'https' and parsed.hostname in {'api.typeform.com','api.eu.typeform.com','api.typeform.eu'} and parsed.path == '/forms/' + form_id + '/responses':
                base = parsed.scheme + '://' + parsed.hostname
            else:
                base = 'https://api.typeform.com'
            data = typeform('/forms/' + form_id + '/responses?page_size=1',base=base)
            answered = int(data.get('total_items', 0))
            warning = None
        except ValueError as ex:
            answered = None
            warning = str(ex)
        target = counts.get(form_id)
        result.append({'id':form_id, 'title':f.get('title') or 'Sin título', 'responses':answered,
                       'target':target, 'percentage':round(answered / target * 100,1) if answered is not None and target else None,
                       'link':f'https://form.typeform.com/to/{form_id}', 'error':warning})
    return result



def build_questions(goal, collective):
    """Plantillas transparentes, sin servicios de IA externos."""
    context = goal.casefold()
    if any(word in context for word in ('turno','horario','descanso','jornada')):
        main = '¿Cómo están afectando los turnos o horarios a tu día a día?'
        improvement = '¿Qué cambiarías de la organización de los turnos?'
    elif any(word in context for word in ('comunicaci','informaci','lider','responsable')):
        main = '¿Recibes la información que necesitas para hacer bien tu trabajo?'
        improvement = '¿Qué mejorarías de la comunicación en tu trabajo?'
    elif any(word in context for word in ('herramient','recurso','equipo','material')):
        main = '¿Tienes las herramientas necesarias para hacer tu trabajo?'
        improvement = '¿Qué herramienta o recurso mejorarías primero?'
    elif any(word in context for word in ('bienestar','carga','estrés','estres','clima','ambiente')):
        main = '¿Cómo valoras tu bienestar en el trabajo actualmente?'
        improvement = '¿Qué cambiarías para mejorar tu bienestar en el trabajo?'
    else:
        main = '¿Cómo valorarías tu experiencia de trabajo en las últimas semanas?'
        improvement = '¿Qué deberíamos mejorar respecto a este tema?'
    return [
        {'type':'opinion_scale','title': main},
        {'type':'opinion_scale','title':'¿Sientes que se escuchan tus necesidades en el trabajo?'},
        {'type':'long_text','title': improvement},
        {'type':'long_text','title':'¿Hay algo que esté funcionando especialmente bien?'}
    ]


def validate_campaign(obj, require_questions=False):
    if not isinstance(obj,dict): raise ValueError('Datos inválidos.')
    title=obj.get('title',''); goal=obj.get('goal',''); collective=obj.get('collective','')
    target=obj.get('target')
    if not isinstance(title,str) or not 3<=len(title.strip())<=120: raise ValueError('Escribe un título de 3 a 120 caracteres.')
    if not isinstance(goal,str) or not 5<=len(goal.strip())<=700: raise ValueError('Escribe un objetivo de 5 a 700 caracteres.')
    if not isinstance(collective,str) or collective not in ('Toda la empresa','Planta','Logística','Comercial','Oficinas','Dirección'): raise ValueError('Elige un colectivo.')
    if not isinstance(target,int) or isinstance(target,bool) or not 1<=target<=1000000: raise ValueError('Indica cuántas personas deben contestar (1 a 1.000.000).')
    if require_questions:
        questions=obj.get('questions')
        if not isinstance(questions,list) or not 3<=len(questions)<=6: raise ValueError('Debes aprobar entre 3 y 6 preguntas.')
        for q in questions:
            if not isinstance(q,dict) or q.get('type') not in ('opinion_scale','long_text') or not isinstance(q.get('title'),str) or not 5<=len(q['title'].strip())<=300:
                raise ValueError('Revisa las preguntas antes de crear la campaña.')
    return title.strip(), goal.strip(), collective, target


def create_campaign(obj):
    title, goal, collective, target = validate_campaign(obj,True)
    fields=[]
    for i,q in enumerate(obj['questions']):
        field={'ref':'q_%d'%(i+1),'title':q['title'].strip(),'type':q['type'],'validations':{'required':False}}
        if q['type']=='opinion_scale':
            field['properties']={'start_at_one':True,'steps':5,'labels':{'left':'Muy mal','right':'Muy bien'}}
        fields.append(field)
    payload={
        'title':title,
        'settings':{'language':'es','is_public':True,'show_progress_bar':True,'progress_bar':'proportion'},
        'welcome_screens':[{'title':title,'properties':{'description':'Consulta de clima laboral · '+collective+'. Respuestas tratadas de forma agregada. No incluyas nombres ni datos personales.','show_button':True,'button_text':'Empezar'}}],
        'fields':fields,
        'thankyou_screens':[{'title':'¡Gracias por participar!'}]
    }
    result=typeform('/forms',method='POST',data=payload)
    form_id=result.get('id')
    if not isinstance(form_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',form_id):
        raise ValueError('Typeform no devolvió un identificador válido. Comprueba la cuenta antes de reintentar.')
    saved=targets();saved[form_id]=target
    try: SETTINGS.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    except OSError: return {'id':form_id,'link':'https://form.typeform.com/to/'+form_id,'warning':'Formulario creado, pero no se pudo guardar la población objetivo localmente.'}
    return {'id':form_id,'link':'https://form.typeform.com/to/'+form_id}


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, payload):
        data = json.dumps(payload,ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            data=(ROOT/'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers(); self.wfile.write(data)
        elif self.path == '/api/forms':
            try: self.respond(200,{'forms':get_forms()})
            except ValueError as e: self.respond(400,{'error':str(e)})
        else: self.respond(404,{'error':'No encontrado'})

    def do_POST(self):
        if self.path not in ('/api/target','/api/campaign-preview','/api/campaigns'): return self.respond(404,{'error':'No encontrado'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>16000: return self.respond(413,{'error':'Solicitud demasiado grande o vacía'})
            obj=json.loads(self.rfile.read(length))
            if self.path == '/api/campaign-preview':
                title,goal,collective,target=validate_campaign(obj)
                return self.respond(200,{'questions':build_questions(goal,collective)})
            if self.path == '/api/campaigns':
                return self.respond(201,create_campaign(obj))
            form_id=obj['id']; count=obj['target']
            if not isinstance(form_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',form_id): raise ValueError('ID de formulario no válido.')
            if not isinstance(count,int) or isinstance(count,bool) or not 1<=count<=10000000: raise ValueError('Introduce una población objetivo válida (mayor que cero).')
            existing=targets();existing[form_id]=count
            SETTINGS.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')
            return self.respond(200,{'ok':True})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            return self.respond(400,{'error':str(exc) if str(exc) else 'Datos no válidos.'})

    def log_message(self, fmt, *args):
        if not self.path.startswith('/api/'): super().log_message(fmt,*args)

if __name__=='__main__':
    print('Panel Damm: http://127.0.0.1:5000')
    ThreadingHTTPServer(('127.0.0.1',5000),Handler).serve_forever()
