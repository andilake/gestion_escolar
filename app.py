### PENDIENTE:
# Apellidos compuestos hacer que se incluyan en el nombre, si el apellido empieza con de o con de la (puedo buscar estas palabras en el apellido o contar si son menos de 3 letras)
# Subida masiva de usuarios
# Hacer pruebas para intentar romper el programa
# Agregar login
## Versión 2:
# Agregar maestros
# Agregar papás
# Agregar botón para descargar en formato moodle


## LIBRERÍAS ##

from datetime import datetime
from flask import flash, Flask, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
import json
import os
import unicodedata


## CONSTANTES ##

DOMINIO = 'colegionuevo.com'
SECCIONES = ["Maternal", "Kinder", "Primaria", "Secundaria", "Preparatoria"]
GRUPOS = ["A", "B", "C", "D", "E", "F", "H", "I", "Q"]
ESTADOS = {"Activo" : 0, "Suspendido" : 1, "Baja" : 2}
ESTADOSV = {v: k for k, v in ESTADOS.items()}
COLORES = {"Activo": "#729869", "Suspendido": "#D69900", "Baja": "#DC3545"}
ADMPASS = "123456"


## CONFIGURACIONES ##

# Configuración para desarrollo
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# Configurar aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = '12345'

# Cerrar sesión al cerrar el navegador
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


## BASES DE DATOS ##

# Configurar base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
db = SQLAlchemy(app)

# Tabla de alumnos
class Alumnos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(50), nullable=False, unique=True)
    estado = db.Column(db.Integer, nullable=False, default=0) # 0 - activo, 1 - suspendido, 2 - baja
    fecha_de_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __init__(self, nombre, apellidos, correo):
        self.nombre = nombre
        self.apellidos = apellidos
        self.correo = correo

    def __repr__(self):
       return f"<Alumno {self.id}: {self.nombre} {self.apellidos}>"
    
    def to_dict(self):
        return {'id': self.id, 'nombre': self.nombre, 'apellidos': self.nombre, 'correo': self.correo, 'estado': ESTADOSV[self.estado], 'estado_num': self.estado, 'fecha_de_creacion': self.fecha_de_creacion}


# Tabla de administradores
class Admins(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(50), nullable=False, unique=True)
    hash = db.Column(db.String(50), nullable=False)

    def __init__(self, usuario, nombre, apellidos, correo, hash):
        self.usuario = usuario
        self.nombre = nombre
        self.apellidos = apellidos
        self.correo = correo
        self.hash = hash

    def __repr__(self):
        return f"<Usuario {self.id}: {self.usuario} - {self.nombre} {self.apellidos}>"
    

# Tabla de grupos
class Grupos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seccion = db.Column(db.String(50), nullable=False)
    grado = db.Column(db.Integer, nullable=False)
    grupo = db.Column(db.String(1), nullable=False)

    def __init__(self, seccion, grado, grupo):
        self.seccion = seccion
        self.grado = grado
        self.grupo = grupo

    def __repr__(self):
       return f"{self.grado}°{self.grupo} de {self.seccion}"


# Alumnos por grupo
alumnos_por_grupo = db.Table('alumnos_por_grupo',
    db.Column('id_alumno', db.Integer, db.ForeignKey('alumnos.id'), nullable=False),
    db.Column('id_grupo', db.Integer, db.ForeignKey('grupos.id'), nullable=False)
)


# Cambios de estado
class CambiosEstado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado_anterior = db.Column(db.Integer, nullable=False)
    estado_nuevo = db.Column(db.Integer, nullable=False)

    def __init__(self, id_alumno, estado_anterior, estado_nuevo):
        self.id_alumno = id_alumno
        self.estado_anterior = estado_anterior
        self.estado_nuevo = estado_nuevo

    def __repr__(self):
        return f'<Alumno: {self.id_alumno} cambió de {self.estado_anterior} a {self.estado_nuevo} el día {self.fecha}>'

# Log de altas y bajas
class Totales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False)
    total = db.Column(db.Integer, nullable=False)

    def __init__(self, fecha, total):
        self.fecha = fecha
        self.total = total

    def __repr__(self):
        return f'<{self.fecha.strftime("%d/%m/%Y")}: {self.total} alumnos inscritos>'


## EJECUCIÓN DE LA APLICACIÓN ##

# Crear la base de datos si no existe al correr la aplicación:
with app.app_context():
    db.create_all()
    db.session.commit()
    # Revisar si la tabla de totales está vacía por fecha y si no, crear el total inicial
    if len(Totales.query.all()) == 0:
        total = 0
        fechas = []
        query = db.session.query(func.date(Alumnos.fecha_de_creacion), func.count(Alumnos.id)) \
                .filter(Alumnos.estado.in_([0, 1])) \
                .group_by(func.date(Alumnos.fecha_de_creacion)) \
                .all()
        for i in query:
            total += i[1]
            fecha = datetime.strptime(i[0], '%Y-%m-%d').date()
            nuevo = Totales(fecha, total)
            db.session.add(nuevo)
        db.session.commit()
    # Crear admin si no existe al correr la aplicación
    if len(Admins.query.all()) == 0:
        nombre = "Admin"
        apellidos = "Adm"
        correo = "admin@" + DOMINIO
        hash = generate_password_hash(ADMPASS)
        usuario = "admin"
        admin = Admins(usuario, nombre, apellidos, correo, hash)
        db.session.add(admin)
        db.session.commit()


## FUNCIONES ##

# Función para agregar al log de altas y bajas
def alta_log(alta):
    totales = db.session.query(func.date(Totales.fecha), Totales.total, Totales.id).order_by(Totales.fecha.desc()).first()
    hoy = datetime.utcnow().strftime('%Y-%m-%d')
    total = (totales.total + 1) if alta else (totales.total - 1)
    if totales[0] == hoy:
        q = Totales.query.filter_by(id=totales.id).first()
        q.total = total
    else:
        fecha = datetime.strptime(hoy, '%Y-%m-%d').date()
        nuevo = Totales(fecha, total)
        db.session.add(nuevo)
    db.session.commit()
    return


# Función para cambio de estado
def cambiar_estado_alumno(usuario, estado):
    cambioestado = CambiosEstado(usuario.id, usuario.estado, estado)
    usuario.estado = estado
    db.session.add(cambioestado)
    return


# Función para normalizar nombres
def normalizar(nombre):
    normalizado = unicodedata.normalize('NFKD', nombre.split()[0]).encode('ASCII', 'ignore').decode('utf-8').lower()
    return normalizado


# Función para crear correos
def crear_correo(nombre, apellidos):
    #Normalizar nombre y apellido
    nombre_norm = normalizar(nombre)
    apellido_norm = normalizar(apellidos)
    # Crear correo
    correo = nombre_norm + "." + apellido_norm
    # Verificar si el correo existe
    existe = Alumnos.query.filter_by(correo=(correo + '@' + DOMINIO)).first()
    contador = ''
    # Si existe, añadir un 0 al correo y el contador
    if existe:
        correo = correo + '0'
        contador = 0
    while existe:
        contador += 1
        existe = Alumnos.query.filter_by(correo=(correo + str(contador) + '@' + DOMINIO)).first()
    # Añadir dominio al correo
    correo = correo + str(contador) + '@' + DOMINIO
    return correo


# Función para consultar alumnos
def consultar_alumnos(grupo_actual, estado):
    # Verificar si se seleccionó una sección, si no, mostrar todos los alumnos
    if grupo_actual["seccion"] == "":
        return None
    # Obtener los grados de la sección seleccionada
    grados = db.session.query(Grupos.grado).filter_by(seccion=grupo_actual["seccion"]).distinct().order_by(Grupos.grado).all()
    # Verificar si hay un grado y un grupo seleccionados
    if grupo_actual["grado"] != "" and grupo_actual["grupo"] != "":
        grupo_actual["grado"] = int(grupo_actual["grado"])
        # Obtener ID de grupo
        query = db.session.query(Grupos.id).filter_by(seccion=grupo_actual["seccion"], grado=grupo_actual["grado"], grupo=grupo_actual["grupo"]).order_by(Grupos.grado).all()
        # Obtener los grupos que hay en el grado
        grupos = db.session.query(Grupos.grupo).filter_by(seccion=grupo_actual["seccion"], grado=grupo_actual["grado"]).distinct().order_by(Grupos.grupo).all()
    # Si no hay un grupo seleccionado, verificar si hay un grado y repetir lo anterior
    elif grupo_actual["grado"] != "":
        grupo_actual["grado"] = int(grupo_actual["grado"])
        query = db.session.query(Grupos.id).filter_by(seccion=grupo_actual["seccion"], grado=grupo_actual["grado"]).order_by(Grupos.grado).all()
        grupos = db.session.query(Grupos.grupo).filter_by(seccion=grupo_actual["seccion"], grado=grupo_actual["grado"]).distinct().order_by(Grupos.grupo).all()
    # Si no hay un grado seleccionado, obtener los ids de todos los grupos de la sección
    else:
        query = db.session.query(Grupos.id).filter_by(seccion=grupo_actual["seccion"]).order_by(Grupos.grado).all()
        grupos = None
    ids_grupo = []
    ids_alumno = []
    # Sacar los ids como una lista
    for i in query:
        ids_grupo.append(i[0])
    # Obtener los ids de los alumnos que pertenecen a los grupos seleccionados
    query_alumnos = db.session.query(alumnos_por_grupo.c.id_alumno).filter(alumnos_por_grupo.c.id_grupo.in_(ids_grupo)).distinct().all()
    for i in query_alumnos:
        ids_alumno.append(i[0])
    # Obtener alumnos
    lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.id.in_(ids_alumno), Alumnos.estado.in_(estado))\
                        .order_by(Alumnos.apellidos)\
                        .all()
    datos = {'lista': lista, 'grados': grados, 'grupos': grupos}
    return datos


# Función para requerir inicio de sesión
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

## PÁGINAS ##

# Página de inicio
@app.route("/")
@login_required
def index():
    secciones = []
    datos_secciones = []
    fechas = []
    datos_fechas = []
    # Obtener alumnos por sección
    query = db.session.query(Grupos.seccion, func.count(Alumnos.id))\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado.in_([0,1]))\
                        .group_by(Grupos.seccion)\
                        .order_by(Grupos.id)\
                        .all()
    for i in query:
        secciones.append(i[0])
        datos_secciones.append(i[1])
    totales = db.session.query(func.date(Totales.fecha), Totales.total).order_by(Totales.fecha).all()
    # Obtener totales por fecha
    for total in totales:
        fechas.append(total[0])
        datos_fechas.append(total[1])
    secciones_json = json.dumps(secciones)
    datos_secciones_json = json.dumps(datos_secciones)
    fechas_json = json.dumps(fechas)
    datos_fechas_json = json.dumps(datos_fechas)
    return render_template("index.html", active="Inicio", secciones=secciones_json, datos_secciones=datos_secciones_json, fechas=fechas_json, datos_fechas=datos_fechas_json)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        # Borrar el user_id si existe
        session.clear()
        user = request.form.get("user")
        password = request.form.get("password")
        # Revisar que se introdujo nombre de usuario y contraseña
        if not user or not password:
            flash("Error al iniciar sesión")
            return redirect(url_for("login")) 
        # Buscar el usuario
        usuario = db.session.query(Admins).filter_by(correo=user).first()
        # Si el usuario existe, revisar si la contraseña es correcta
        if not usuario or not check_password_hash(usuario.hash, password):
            flash("Nombre de usuario o contraseña incorrectos")
            return redirect(url_for("login")) 

        # Recordar usuario
        session["user_id"] = usuario.id

        # Redirigin al usuario a la página de inicio
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


# Ver alumnos
@app.route("/lista_alumnos", methods=["GET", "POST"])
@login_required
def lista_alumnos():
    if request.method == "POST":
        grupo_actual = {}
        # Obtener seccion, grado y grupo actuales
        grupo_actual["seccion"] = request.form.get("seccion")
        grupo_actual["grado"] = request.form.get("grado")
        grupo_actual["grupo"] = request.form.get("grupo")
        # Verificar si se requiere consultar suspendidos y establecer el estado
        suspendidos = True if request.form.get("suspendidos") == "on" else False
        estado = [0, 1] if suspendidos else [0]
        # Obtener las secciones
        secciones = db.session.query(Grupos.seccion).distinct().all()
        datos = consultar_alumnos(grupo_actual, estado)
        if datos:        
            return render_template("lista_alumnos.html", active="Lista de alumnos", lista=datos['lista'] , estados=ESTADOSV, grupo_actual=grupo_actual, secciones=secciones, grados=datos['grados'], grupos=datos['grupos'], suspendidos=suspendidos)
        else:
            lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado.in_(estado))\
                        .order_by(Alumnos.apellidos)\
                        .all()
            return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None, suspendidos=suspendidos)

    else:
        # Mostrar todos los alumnos activos
        estado = 0
        lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado == estado)\
                        .order_by(Alumnos.apellidos)\
                        .all()
        print(lista)
        secciones = db.session.query(Grupos.seccion).distinct().all()
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None)


# Alumno nuevo
@app.route("/alta_alumno", methods=["GET", "POST"])
@login_required
def alta_alumno():

    if request.method == "POST":
        # Obtener datos de alumno
        nombre = request.form.get("nombre").title()
        apellidos = request.form.get("apellidos").title()
        seccion = request.form.get("seccion")
        grado = request.form.get("grado")
        grupo = request.form.get("grupo")
        correo = crear_correo(nombre, apellidos)
        # Agregar usuario a la base de datos
        alumno = Alumnos(nombre, apellidos, correo)
        db.session.add(alumno)
        db.session.commit()
        # Actualizar log de altas y bajas
        alta_log(True)
        # Obtener id de grupo y alumno
        id_grupo = db.session.query(Grupos.id).filter_by(seccion=seccion, grado=grado, grupo=grupo).first()
        id_alumno = db.session.query(Alumnos.id).filter_by(correo=correo).first()[0]
        # Comprobar que exista el alumno y el grupo
        if id_grupo and id_alumno:
            id_grupo = id_grupo[0]
            db.session.execute(alumnos_por_grupo.insert().values(id_alumno=id_alumno, id_grupo=id_grupo))
            db.session.commit()
        # Redireccionar a la página de todos los alumnos
        return redirect("/lista_alumnos")

    else:
        seccion = db.session.query(Grupos.seccion).distinct().all()
        return render_template("editar_alumno.html", active="Alta alumno", secciones=seccion)


@app.route("/bajas_alumnos")
@login_required
def bajas_alumnos():
    # Obtener última fecha de eliminación
    subconsulta = db.session.query(CambiosEstado.id_alumno, db.func.max(CambiosEstado.fecha).label('max_fecha'))\
                        .filter(CambiosEstado.estado_nuevo == 2)\
                        .group_by(CambiosEstado.id_alumno)\
                        .subquery()
    # Obtener alumnos eliminados
    lista = db.session.query(Alumnos, CambiosEstado.fecha.label('fecha_de_eliminacion'))\
                  .join(subconsulta, Alumnos.id == subconsulta.c.id_alumno)\
                  .join(CambiosEstado, db.and_(CambiosEstado.id_alumno == subconsulta.c.id_alumno, CambiosEstado.fecha == subconsulta.c.max_fecha))\
                  .filter(Alumnos.estado == 2)\
                  .order_by(subconsulta.c.max_fecha.desc())\
                  .all()
    return render_template("bajas_alumnos.html", active="Bajas alumnos", lista=lista)


# Editar alumno
@app.route("/editar_alumno", methods=["GET","POST"])
@login_required
def editar_alumno():
    if request.method == "POST":
        # Obtener datos de alumno
        nombre = request.form.get("nombre").title()
        apellidos = request.form.get("apellidos").title()
        estado = int(request.form.get("estado"))
        id = request.form.get("id")
        seccion = request.form.get("seccion")
        grado = request.form.get("grado")
        grupo = request.form.get("grupo")
        actualizar_correo = request.form.get("correo")
        alumno = db.session.query(Alumnos).filter_by(id=id).first()
        # Quitar números y arrobas al correo
        correo = alumno.correo.split('@')[0]
        correo = ''.join(filter(lambda x: not x.isdigit(), correo))
        # Verificar si es necesario actualizar el correo
        if (normalizar(nombre) + '.' + normalizar(apellidos) != correo) and actualizar_correo == "si":
            correo = crear_correo(nombre, apellidos)
            alumno.correo = correo
        alumno.nombre = nombre
        alumno.apellidos = apellidos
        # Actualizar tabla de cambios de estado si hubo un cambio
        if estado != alumno.estado:
            cambioestado = CambiosEstado(id, alumno.estado, estado)
            alumno.estado = estado
            db.session.add(cambioestado)
        # Obtener id de grupo
        id_grupo = db.session.query(Grupos.id).filter_by(seccion=seccion, grado=grado, grupo=grupo).first()
        alumno_grupo = db.session.query(alumnos_por_grupo).filter_by(id_alumno=id).first()
        # Revisar si se añadió el alumno a un grupo
        if id_grupo:
            id_grupo = id_grupo[0]
            # Revisar si el alumno pertenece a un grupo y actualizarlo o agregarlo
            if alumno_grupo:
                db.session.query(alumnos_por_grupo).filter_by(id_alumno=id).update({'id_grupo': id_grupo})
            else:
                db.session.execute(alumnos_por_grupo.insert().values(id_alumno=id, id_grupo=id_grupo))
        # Subir cambios a la base de datos
        db.session.commit()
        return redirect("/lista_alumnos")

    else:
        # Obtener alumno
        id_alumno = request.args.get("id")
        alumno = db.session.query(Alumnos).filter_by(id=id_alumno).first()
        # Obtener grupo y listado de grados y grupos
        id_grupo = db.session.query(alumnos_por_grupo.c.id_grupo).filter_by(id_alumno=alumno.id).first()
        if id_grupo:
            id_grupo = id_grupo[0]
            grupo_actual = db.session.query(Grupos).filter_by(id=id_grupo).first()
            grados = db.session.query(Grupos.grado).filter_by(seccion=grupo_actual.seccion).distinct().all()
            grupos = db.session.query(Grupos.grupo).filter_by(seccion=grupo_actual.seccion, grado=grupo_actual.grado).distinct().all()
        else:
            grupo_actual = None
            grados = None
            grupos = None
        secciones = db.session.query(Grupos.seccion).distinct().all()
        return render_template("editar_alumno.html", editar=True, active="Alumno", secciones=secciones, grados=grados, grupos=grupos, grupo_actual=grupo_actual, alumno=alumno, colores=COLORES, estados=ESTADOSV)


# Ver alumno
@app.route('/ver_alumno')
@login_required
def ver_alumno():
    # Obtener alumno
    id = request.args.get("id")
    alumno = db.session.query(Alumnos).filter_by(id=id).first()
    # Obtener cambios
    cambios = db.session.query(CambiosEstado).filter_by(id_alumno=id).order_by(CambiosEstado.fecha.desc()).all()
    id_grupo = db.session.query(alumnos_por_grupo.c.id_grupo).filter_by(id_alumno=id).first()
    # Obtener grupo
    if id_grupo:
        id_grupo = id_grupo[0]
        grupo_actual = db.session.query(Grupos).filter_by(id=id_grupo).first()
    else:
        grupo_actual = None
    return render_template("ver_alumno.html", active="Alumno", grupo_actual=grupo_actual, alumno=alumno, colores=COLORES, cambios=cambios, estados=ESTADOSV)


# Suspender y reactivar alumno
@app.route('/suspender_alumno', methods=["POST"])
@login_required
def suspender_alumno():
    # Obtener usuario y grupo actual
    id = request.form.get("id")
    alumno = Alumnos.query.get(id)
    grupo_actual = {'seccion': request.form.get("ga_seccion"), 'grado': request.form.get("ga_grado"), 'grupo': request.form.get("ga_grupo")}
    # Verificar si se requiere consultar suspendidos y establecer el estado
    suspendidos =  True if request.form.get("susp") == "True" else False
    estados = [0, 1] if suspendidos else [0]
    # Obtener al alumno y ver si se requiere suspender o activar
    suspender = request.form.get("suspender")
    estado = 1 if suspender == "si" else 0
    # Obtener las secciones
    secciones = db.session.query(Grupos.seccion).distinct().all()
    # Suspender el alumno si existe
    if alumno:
        cambiar_estado_alumno(alumno, estado)
        db.session.commit()
        print(f"{alumno} ha sido {'suspendido' if suspender == 'si' else 'reactivado'}")
    # Obtener lista de alumnos
    datos = consultar_alumnos(grupo_actual, estados)
    if datos:        
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=datos['lista'] , estados=ESTADOSV, grupo_actual=grupo_actual, secciones=secciones, grados=datos['grados'], grupos=datos['grupos'], suspendidos=suspendidos)
    else:
        lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado.in_(estados))\
                        .order_by(Alumnos.apellidos)\
                        .all()
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None, suspendidos=suspendidos)


# Suspender alumno desde edición
@app.route('/suspender_alumno_edicion', methods=["POST"])
@login_required
def suspender_alumno_edicion():
    # Obtener al alumno y ver si se requiere suspender o activar
    id_alumno = request.form.get("id")
    suspender = request.form.get("suspender")
    alumno = Alumnos.query.get(id_alumno)
    estado = 1 if suspender == "si" else 0
    # Suspender el alumno si existe
    if alumno:
        cambiar_estado_alumno(alumno, estado)
        db.session.commit()
        print(f"{alumno} ha sido {'suspendido' if suspender == 'si' else 'reactivado'}")
   # Obtener grupo y listado de grados y grupos
    id_grupo = db.session.query(alumnos_por_grupo.c.id_grupo).filter_by(id_alumno=alumno.id).first()
    if id_grupo:
        id_grupo = id_grupo[0]
        grupo_actual = db.session.query(Grupos).filter_by(id=id_grupo).first()
        grados = db.session.query(Grupos.grado).filter_by(seccion=grupo_actual.seccion).distinct().all()
        grupos = db.session.query(Grupos.grupo).filter_by(seccion=grupo_actual.seccion, grado=grupo_actual.grado).distinct().all()
    else:
        grupo_actual = None
        grados = None
        grupos = None
    secciones = db.session.query(Grupos.seccion).distinct().all()
    return render_template("editar_alumno.html", editar=True, active="Alumno", secciones=secciones, grados=grados, grupos=grupos, grupo_actual=grupo_actual, alumno=alumno, colores=COLORES, estados=ESTADOSV)


# Eliminar alumno
@app.route('/eliminar_alumno', methods=["POST"])
@login_required
def eliminar_alumno():
    # Obtener alumno
    id = request.form.get("seleccionado")
    alumno = Alumnos.query.get(id)
    # Obtener el grupo actual
    grupo_actual = {'seccion': request.form.get("ga_seccion"), 'grado': request.form.get("ga_grado"), 'grupo': request.form.get("ga_grupo")}
    # Verificar si se requiere consultar suspendidos y establecer el estado
    suspendidos =  True if request.form.get("susp") == "True" else False
    estados = [0, 1] if suspendidos else [0]
    # Obtener las secciones
    secciones = db.session.query(Grupos.seccion).distinct().all()
    # Borrar el alumno si existe
    if alumno:
        cambiar_estado_alumno(alumno, 2)
        db.session.commit()
        # Actualizar log de altas y bajas
        alta_log(False)
        print(f"{alumno} ha sido dado de baja")
    # Obtener lista de alumnos
    datos = consultar_alumnos(grupo_actual, estados)
    if datos:        
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=datos['lista'] , estados=ESTADOSV, grupo_actual=grupo_actual, secciones=secciones, grados=datos['grados'], grupos=datos['grupos'], suspendidos=suspendidos)
    else:
        lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado.in_(estados))\
                        .order_by(Alumnos.apellidos)\
                        .all()
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None, suspendidos=suspendidos)


# Eliminar alumno desde edición
@app.route('/eliminar_alumno_edicion', methods=["POST"])
@login_required
def eliminar_alumno_edicion():
    # Obtener alumno
    id = request.form.get("id")
    alumno = Alumnos.query.get(id)
    # Borrar el alumno si existe
    if alumno:
        cambiar_estado_alumno(alumno, 2)
        db.session.commit()
        # Actualizar log de altas y bajas
        alta_log(False)
        # Actualizar log de altas y bajas
        alta_log(False)
        print(f"{alumno} ha sido dado de baja")
    # Obtener las secciones
    secciones = db.session.query(Grupos.seccion).distinct().all()
    # Obtener lista de alumnos
    estado = 0
    lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado == estado)\
                        .order_by(Alumnos.apellidos)\
                        .all()
    return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None, suspendidos=False)


# Recuperar alumno
@app.route('/recuperar_alumno', methods=["POST"])
@login_required
def recuperar_alumno():
    # Obtener alumno
    id = request.form.get("id")
    alumno = Alumnos.query.get(id)
    if alumno:
        cambiar_estado_alumno(alumno, 0)
        db.session.commit()
        # Actualizar log de altas y bajas
        alta_log(True)
        print(f"{alumno} ha sido recuperado")
    # Obtener lista de alumnos
    return redirect("/bajas_alumnos")


# Eliminar alumno permanentemente
@app.route('/eliminar_permanentemente', methods=["POST"])
@login_required
def eliminar_permanentemente():
    # Obtener usuario
    id = request.form.get("seleccionado")
    alumno = Alumnos.query.get(id)
    # Borrar el usuario si existe
    if alumno:
        db.session.execute(alumnos_por_grupo.delete().where(alumnos_por_grupo.c.id_alumno==id))
        db.session.delete(alumno)
        CambiosEstado.query.filter_by(id_alumno=id).delete()
        db.session.commit()
        print(f"{alumno} ha sido borrado de la base de datos")
    return redirect("/bajas_alumnos")


# Eliminar o suspender múltiples alumnos
@app.route('/eliminar_alumnos', methods=["POST"])
@login_required
def eliminar_alumnos():
    # Obtener ids alumnos y convertirlas a entero
    ids_alumnos = json.loads(request.form.get("seleccionados"))
    ids_alumnos = [int(x) for x in ids_alumnos]
    # Obtener grupo actual
    grupo_actual = {'seccion': request.form.get("ga_seccion"), 'grado': request.form.get("ga_grado"), 'grupo': request.form.get("ga_grupo")}
    # Verificar si se requiere consultar suspendidos y establecer el estado
    suspendidos =  True if request.form.get("susp") == "True" else False
    estados = [0, 1] if suspendidos else [0]
    # Revisar si se tienen que suspender, eliminar o activar 
    accion = request.form.get("accion")
    estado = 2 if accion == "eliminar" else 1 if accion == "suspender" else 0
    texto = "dado de baja" if accion == "eliminar" else "suspendido"
    # Obtener las secciones
    secciones = db.session.query(Grupos.seccion).distinct().all()
    for id in ids_alumnos:
        alumno = Alumnos.query.filter_by(id=id).first()
        # Revisar si el alumno existe
        if alumno:
            cambiar_estado_alumno(alumno, estado)
            db.session.commit()
            if accion == "eliminar":
                # Actualizar log de altas y bajas
                alta_log(False)
            print(f"{alumno} ha sido {texto}")
    # Obtener lista de alumnos
    datos = consultar_alumnos(grupo_actual, estados)
    if datos:        
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=datos['lista'] , estados=ESTADOSV, grupo_actual=grupo_actual, secciones=secciones, grados=datos['grados'], grupos=datos['grupos'], suspendidos=suspendidos)
    else:
        lista = db.session.query(Alumnos, Grupos)\
                        .join(alumnos_por_grupo, Alumnos.id == alumnos_por_grupo.c.id_alumno)\
                        .join(Grupos, Grupos.id == alumnos_por_grupo.c.id_grupo)\
                        .filter(Alumnos.estado.in_(estados))\
                        .order_by(Alumnos.apellidos)\
                        .all()
        return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, grupo_actual=None, secciones=secciones, grados=None, grupos=None, suspendidos=suspendidos)


# Eliminar varios alumnos permanentemente
@app.route('/eliminar_alumnos_permanentemente', methods=["POST"])
@login_required
def eliminar_alumnos_permanentemente():
    # Obtener ids alumnos y convertirlas a entero
    ids_alumnos = json.loads(request.form.get("seleccionados"))
    ids_alumnos = [int(x) for x in ids_alumnos]
    for id in ids_alumnos:
        alumno = Alumnos.query.get(id)
        # Borrar el usuario si existe
        if alumno:
            db.session.execute(alumnos_por_grupo.delete().where(alumnos_por_grupo.c.id_alumno==id))
            db.session.delete(alumno)
            CambiosEstado.query.filter_by(id_alumno=id).delete()
            db.session.commit()
            print(f"{alumno} ha sido borrado de la base de datos")
    return redirect("/bajas_alumnos")


# Recuperar varios alumnos
@app.route('/recuperar_alumnos', methods=["POST"])
@login_required
def recuperar_alumnos():
    # Obtener ids alumnos y convertirlas a entero
    ids_alumnos = json.loads(request.form.get("seleccionados"))
    ids_alumnos = [int(x) for x in ids_alumnos]
    for id in ids_alumnos:
        alumno = Alumnos.query.get(id)
        # Borrar el usuario si existe
        if alumno:
            cambiar_estado_alumno(alumno, 0)
            db.session.commit()
            # Actualizar log de altas y bajas
            alta_log(True)
            print(f"{alumno} ha sido recuperado")
    return redirect("/bajas_alumnos")


# Grupo nuevo
@app.route("/nuevo_grupo", methods=["GET", "POST"])
@login_required
def nuevo_grupo():

    if request.method == "POST":
        # Obtener datos del grupo
        seccion = request.form.get("seccion").title()
        grado = int(request.form.get("grado"))
        grupo = request.form.get("grupo").upper()
        # Agregar a la base de datos
        if grupo in GRUPOS and grado in range (1,7) and seccion in SECCIONES:
            query = Grupos(seccion, grado, grupo)
            print(query)
            db.session.add(query)
            db.session.commit()
        else:
            print("Error")

        # Redireccionar a la página de todos los alumnos
        return redirect("/nuevo_grupo")

    else:
        return render_template("nuevo_grupo.html", active="Nuevo grupo", secciones=SECCIONES, grupos=GRUPOS)


# Lista de grupos
@app.route("/lista_grupos")
@login_required
def lista_grupos():
    grupos = db.session.query(Grupos).all()
    return render_template("lista_grupos.html", active="Lista de grupos", grupos=grupos, secciones=SECCIONES)

# Rellenar grado
@app.route('/grados', methods=['POST'])
def grados():
    # Obtener la seccion
    seccion = request.form.get('seccion')
    # Obtener los grados que hay en la seccion
    grados = db.session.query(Grupos.grado).filter_by(seccion=seccion).distinct().order_by(Grupos.grado).all()
    # Crear una opción inicial para el selector
    opciones = '<option disabled selected value="">Grado</option>'
    for grado in grados:
        if grado[0] == "":
            opciones += '<option value="">N/A</option>'
        else:
            opciones += '<option value="' + str(grado[0]) + '">' + str(grado[0]) + '</option>'
    return opciones


# Rellenar grupo
@app.route('/grupos', methods=['POST'])
@login_required
def grupos():
    seccion = request.form.get('seccion')
    grado = request.form.get('grado')
    grupos = db.session.query(Grupos.grupo).filter_by(seccion=seccion, grado=grado).filter(Grupos.grupo != "").distinct().order_by(Grupos.grupo).all()
    opciones = '<option disabled selected value="">Grupo</option>'
    for grupo in grupos:
        opciones += '<option value="' + grupo[0] + '">' + grupo[0] + '</option>'
    # Poner hasta abajo opción N/A
    if db.session.query(Grupos.grupo).filter_by(seccion=seccion, grado=grado).filter(Grupos.grupo == "").first():
        opciones += '<option value="">N/A</option>'
    return opciones


# Obtener alumnos de la seccion
@app.route('/alumnos_seccion', methods=['POST'])
@login_required
def alumnos_seccion():
    # Obtener la seccion
    seccion = request.form.get('seccion')
    # Obtener los grados que hay en la seccion
    query = db.session.query(Grupos.id, Grupos.grado).filter_by(seccion=seccion).order_by(Grupos.grado).all()
    ids_grupo = []
    ids_alumno = []
    grados = []
    for i in query:
        ids_grupo.append(i[0])
        if(i[1] != ""):
            grados.append(i[1])
    grados = list(set(grados))
    grados.sort()
    query_alumnos = db.session.query(alumnos_por_grupo.c.id_alumno).filter(alumnos_por_grupo.c.id_grupo.in_(ids_grupo)).distinct().all()
    for i in query_alumnos:
        ids_alumno.append(i[0])
    estados = [0, 1]
    alumnos = Alumnos.query.filter(Alumnos.id.in_(ids_alumno), Alumnos.estado.in_(estados)).all()
    lista = [a.to_dict() for a in alumnos]
    # Crear una opción inicial para el selector
    opciones = '<option selected value="">Grado</option>'
    for grado in grados:
        opciones += '<option value="' + str(grado) + '">' + str(grado) + '</option>'
    return jsonify({'grados': opciones, 'lista': lista})

# python
# from app import app, db
# app.app_context().push()
# db.create_all()

# set FLASK_ENV=development
# $env:FLASK_DEBUG=1