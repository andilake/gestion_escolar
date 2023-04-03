### PENDIENTE:
# Dashboard
# Subida masiva de usuarios
# Agregar vistas por grupo
# Hacer pruebas para intentar romper el programa
# Recuperar eliminados seleccionados
# Poner los botones de agregar, eliminar, suspender, abajo de la tabla
# Hacer el filtro por grupo desde lista de alumnos, hacer que obtenga la sección, grado y grupo desde el formulario y que vuelva a recargarse cada que seleccione un grupo nuevo
## Versión 2:
# Agregar maestros
# Agregar papás
# Agregar botón para descargar en formato moodle


# Importar librerías
from datetime import datetime
from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import json
import unicodedata

# Configurar aplicación
app = Flask(__name__)

# Constantes
DOMINIO = 'colegionuevo.com'
SECCIONES = ["Maternal", "Kinder", "Primaria", "Secundaria", "Preparatoria"]
GRUPOS = ["A", "B", "C", "D", "E", "F", "H", "I", "Q"]
ESTADOS = {"Activo" : 0, "Suspendido" : 1, "Baja" : 2}
ESTADOSV = {v: k for k, v in ESTADOS.items()}
COLORES = {"Activo": "#729869", "Suspendido": "#D69900", "Baja": "#DC3545"}


# Configurar sesión
# Cerrar sesión al cerrar el navegador
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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
       return f"<{self.grado}°{self.grupo} de {self.seccion}>"


# Alumnos por grupo
alumnos_por_grupo = db.Table('alumnos_por_grupo',
    db.Column('id_alumno', db.Integer, db.ForeignKey('alumnos.id'), nullable=False),
    db.Column('id_grupo', db.Integer, db.ForeignKey('grupos.id'), nullable=False)
)


# Log de altas y bajas
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


# Crear la base de datos si no existe al correr la aplicación:
with app.app_context():
    db.create_all()
    db.session.commit()


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


# Página de inicio
@app.route("/")
def index():
    return render_template("index.html", active="Inicio")


# Ver alumnos
@app.route("/lista_alumnos")
def lista_alumnos():
    # Filtrar alumnos eliminados
    estados = [0, 1]
    lista = Alumnos.query.filter(Alumnos.estado.in_(estados)).all()
    seccion = db.session.query(Grupos.seccion).distinct().all()
    titulo = "Lista general de alumnos"
    return render_template("lista_alumnos.html", active="Lista de alumnos", lista=lista, estados=ESTADOSV, titulo=titulo, grupo_actual=None, secciones=seccion)


# Alumno nuevo
@app.route("/alta_alumno", methods=["GET", "POST"])
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
        return render_template("editar_alumno.html", editar=True, active="Alumno", secciones=secciones, grados=grados, grupos=grupos, grupo_actual=grupo_actual, alumno=alumno, estados=ESTADOS)


# Ver alumno
@app.route('/ver_alumno')
def ver_alumno():
    # Obtener alumno
    id_alumno = request.args.get("id")
    alumno = db.session.query(Alumnos).filter_by(id=id_alumno).first()
    cambios = db.session.query(CambiosEstado).filter_by(id_alumno=id_alumno).order_by(CambiosEstado.fecha.desc()).all()
    id_grupo = db.session.query(alumnos_por_grupo.c.id_grupo).filter_by(id_alumno=alumno.id).first()
    if id_grupo:
        id_grupo = id_grupo[0]
        grupo_actual = db.session.query(Grupos).filter_by(id=id_grupo).first()
    else:
        grupo_actual = None
    estado = ESTADOSV[alumno.estado]
    print(cambios)
    return render_template("ver_alumno.html", ver=True, active="Alumno", grupo_actual=grupo_actual, alumno=alumno, estado=estado, colores=COLORES, cambios=cambios, estados=ESTADOSV)


# Suspender y reactivar alumno
@app.route('/suspender_alumno', methods=["POST"])
def suspender_alumno():
    # Obtener usuario
    id = request.form.get("id")
    suspender = request.form.get("suspender")
    alumno = Alumnos.query.get(id)
    estado = 1 if suspender == "si" else 0
    # Borrar el usuario si existe
    if alumno:
        cambiar_estado_alumno(alumno, estado)
        db.session.commit()
        print(f"{alumno} ha sido {'suspendido' if suspender == 'si' else 'reactivado'}")
    return redirect("/lista_alumnos")


# Eliminar usuario
@app.route('/eliminar_usuario', methods=["POST"])
def eliminar_usuario():
    # Obtener usuario
    id_usuario = request.form.get("seleccionado")
    tabla = request.form.get("tabla")
    if tabla == "Alumnos":
        usuario = Alumnos.query.get(id_usuario)
    else:
        print("Tabla no encontrada")
        return redirect("/lista_alumnos")
    # Borrar el usuario si existe
    if usuario:
        cambiar_estado_alumno(usuario, 2)
        db.session.commit()
        print(f"{usuario} ha sido dado de baja")
    return redirect("/lista_alumnos")


# Eliminar usuario permanentemente
@app.route('/eliminar_permanentemente', methods=["POST"])
def eliminar_permanentemente():
    # Obtener usuario
    id_usuario = request.form.get("seleccionado")
    tabla = request.form.get("tabla")
    if tabla == "Alumnos":
        usuario = Alumnos.query.get(id_usuario)
    else:
        print("Tabla no encontrada")
        return redirect("/lista_alumnos")
    # Borrar el usuario si existe
    if usuario:
        db.session.execute(alumnos_por_grupo.delete().where(alumnos_por_grupo.c.id_alumno==id_usuario))
        db.session.delete(usuario)
        CambiosEstado.query.filter_by(id_alumno=id_usuario).delete()
        db.session.commit()
        print(f"{usuario} ha sido borrado de la base de datos")
    return redirect("/bajas_alumnos")


# Eliminar o suspender múltiples usuarios
@app.route('/eliminar_usuarios', methods=["POST"])
def eliminar_usuarios():
    # Obtener usuarios
    ids_usuarios = json.loads(request.form.get("seleccionados"))
    accion = request.form.get("accion")
    # Revisar si se tiene que suspender o eliminar
    estado = 2 if accion == "eliminar" else 1
    texto = "dado de baja" if accion == "eliminar" else "suspendido"
    print(accion)
    ids_usuarios = [int(x) for x in ids_usuarios]
    tabla = request.form.get("tabla")
    for id in ids_usuarios:
        if tabla == "Alumnos":
            usuario = Alumnos.query.filter_by(id=id).first()
            # Revisar si el usuario existe
            if usuario:
                cambiar_estado_alumno(usuario, estado)
                print(f"{usuario} ha sido {texto}")
        else:
            print("Tabla no encontrada")
            return redirect("/lista_alumnos")
    db.session.commit()
    return redirect("/lista_alumnos")


# Grupo nuevo
@app.route("/nuevo_grupo", methods=["GET", "POST"])
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
    print(lista)
    return jsonify({'grados': opciones, 'lista': lista})

# python
# from app import app, db
# app.app_context().push()
# db.create_all()

# set FLASK_ENV=development
# $env:FLASK_DEBUG=1