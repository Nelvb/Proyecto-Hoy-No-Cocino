"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from api.models import db, Usuario, Reserva, Restaurantes_Favoritos, Valoracion, Restaurantes
from api.utils import generate_sitemap, APIException
from flask_cors import CORS
from datetime import datetime, timezone
import re  # Para validación de email, contraseña y teléfono
#Cloudinary
import cloudinary.uploader

api = Blueprint('api', __name__)

# Allow CORS requests to this API
CORS(api)

# Validar formato de email
def is_valid_email(email):
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_regex, email)

# Validar formato de contraseña (al menos una mayúscula y un número)
def is_valid_password(password):
    if len(password) < 8 or len(password) > 16:
        return False
    if not re.search(r'[A-Z]', password):  # Al menos una mayúscula
        return False
    if not re.search(r'[0-9]', password):  # Al menos un número
        return False
    return True

# Validar formato de teléfono
def is_valid_phone(phone):
    phone_regex = r'^[\d\+\-]+$'  # Permitir solo números, + y -
    if len(phone) < 9:  # Al menos 9 caracteres
        return False
    if not re.match(phone_regex, phone):
        return False
    return True

# Implementar la ruta /signup para el registro de usuarios:
@api.route('/signup', methods=['POST'])
def signup():
    body = request.get_json()
    email = body.get('email')
    password = body.get('password')
    nombres = body.get('nombres')
    apellidos = body.get('apellidos')
    telefono = body.get('telefono')

    # Validaciones de campos
    if not email or not password or not nombres or not apellidos or not telefono:
        return jsonify({'msg': 'Faltan datos'}), 400

    if not is_valid_email(email):
        return jsonify({'msg': 'Formato de email no válido'}), 400

    if not is_valid_password(password):
        return jsonify({'msg': 'La contraseña debe tener entre 8 y 16 caracteres, al menos una mayúscula y un número'}), 400

    if not is_valid_phone(telefono):
        return jsonify({'msg': 'Formato de teléfono no válido. Debe contener al menos 9 caracteres y solo números, +, y -'}), 400

    # Verificar si el usuario ya existe
    if Usuario.query.filter_by(email=email).first():
        return jsonify({'msg': 'El usuario ya existe'}), 409  # Conflicto

    # Crear el nuevo usuario
    new_user = Usuario(
        email=email,
        nombres=nombres,
        apellidos=apellidos,
        telefono=telefono,
        creado=datetime.now(timezone.utc)
    )
    new_user.set_password(password)  # Genera el hash de la contraseña
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'msg': 'Usuario registrado con éxito'}), 201

# Implementar la ruta /login para iniciar sesión:
@api.route('/login', methods=['POST'])
def login():
    body = request.get_json()
    email = body.get('email')
    password = body.get('password')

    if not email or not password:
        return jsonify({'msg': 'Credenciales inválidas'}), 401

    # Verificar si el usuario existe en la base de datos
    user = Usuario.query.filter_by(email=email).first()
    if user is None:
        return jsonify({'msg': 'El usuario no está registrado'}), 404

    # Verificar si la contraseña es correcta
    if not user.check_password(password):
        return jsonify({'msg': 'Contraseña incorrecta'}), 401

    # Generar el Access Token y Refresh Token
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user_name': user.nombres  # Aquí envías el nombre del usuario
    }), 200

# Ruta para generar un nuevo Access Token usando el Refresh Token
@api.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    return jsonify({
        'access_token': new_access_token
    }), 200

# Ruta protegida con JWT, requiere token válido
@api.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()  # Recupera el ID del usuario a partir del JWT
    user = Usuario.query.get(current_user_id)

    if user is None:
        return jsonify({'msg': 'Usuario no encontrado'}), 404

    return jsonify({
        'id': user.id,
        'email': user.email,
        'nombres': user.nombres,
        'apellidos': user.apellidos,
        'telefono': user.telefono,
        'creado': user.creado.isoformat()
    }), 200

# Ruta para validar un token JWT
@api.route('/validate-token', methods=['GET'])
@jwt_required()
def validate_token():
    current_user_id = get_jwt_identity()  # Recupera el ID del usuario del JWT
    user = Usuario.query.get(current_user_id)

    if user is None:
        return jsonify({'msg': 'Usuario no encontrado'}), 404

    return jsonify({'msg': 'Token válido', 'user_id': user.id, 'email': user.email}), 200

# Obtener todos los usuarios (GET /usuarios)
@api.route('/usuarios', methods=['GET'])
def get_all_users():
    usuarios = Usuario.query.all()
    return jsonify([usuario.serialize() for usuario in usuarios]), 200

# Obtener un usuario por su ID (GET /usuario/<int:usuario_id>)
@api.route('/usuario/<int:usuario_id>', methods=['GET'])
@jwt_required()
def get_user(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'msg': 'Usuario no encontrado'}), 404
    
    return jsonify(usuario.serialize()), 200

# Actualiza un usuario (PUT /usuario/<int:usuario_id>)
@api.route('/usuario/<int:usuario_id>', methods=['PUT'])
@jwt_required()
def update_user(usuario_id):
    body = request.get_json()
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        return jsonify({'msg': 'Usuario no encontrado'}), 404
    
    # Actualiza datos del usuario
    usuario.email = body.get('email', usuario.email)
    usuario.nombres = body.get('nombres', usuario.nombres)
    usuario.apellidos = body.get('apellidos', usuario.apellidos)
    usuario.telefono = body.get('telefono', usuario.telefono)

    if 'password' in body:
        usuario.set_password(body['password'])  # Actualizar la contraseña si se proporciona

    db.session.commit()

    return jsonify({'msg': 'Usuario actualizado con éxito'}), 200

# Eliminar un usuario (DELETE /usuario/<int:usuario_id>) 
@api.route('/usuario/<int:usuario_id>', methods=['DELETE'])
@jwt_required()
def delete_user(usuario_id):
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        return jsonify({'msg': 'Usuario no encontrado'}), 404

    db.session.delete(usuario)
    db.session.commit()

    return jsonify({'msg': 'Usuario eliminado con éxito'}), 200

# Crear un restaurante (POST /restaurantes)
@api.route('/signup/restaurante', methods=['POST'])
def signup_restaurante():
    body = request.get_json()

    nombre = body.get('nombre')
    email = body.get('email')
    direccion = body.get('direccion')
    latitud = body.get('latitud')
    longitud = body.get('longitud')
    telefono = body.get('telefono')
    cubiertos = body.get('cubiertos')
    cantidad_mesas = body.get('cantidad_mesas')
    franja_horaria = body.get('franja_horaria')
    reservas_por_dia = body.get('reservas_por_dia')
    categorias_id = body.get('categorias_id')

    # Validaciones de campos obligatorios
    if not nombre or not email or not direccion:
        return jsonify({'msg': 'Faltan datos obligatorios'}), 400

    if Restaurantes.query.filter_by(email=email).first():
        return jsonify({'msg': 'El restaurante ya existe'}), 409

    # Crear el nuevo restaurante
    nuevo_restaurante = Restaurantes(
        nombre=nombre,
        email=email,
        direccion=direccion,
        latitud=latitud,
        longitud=longitud,
        telefono=telefono,
        cubiertos=cubiertos,
        cantidad_mesas=cantidad_mesas,
        franja_horaria=franja_horaria,
        reservas_por_dia=reservas_por_dia,
        categorias_id=categorias_id
    )
    
    db.session.add(nuevo_restaurante)
    db.session.commit()

    return jsonify({'msg': 'Restaurante registrado con éxito'}), 201


# Implementar la ruta /login/restaurante para iniciar sesión de restaurantes
@api.route('/login/restaurante', methods=['POST'])
def login_restaurante():
    body = request.get_json()
    email = body.get('email')
    password = body.get('password')

    if not email or not password:
        return jsonify({'msg': 'Credenciales inválidas'}), 401

    # Verificar si el restaurante existe en la base de datos
    restaurante = Restaurantes.query.filter_by(email=email).first()
    if restaurante is None:
        return jsonify({'msg': 'El restaurante no está registrado'}), 404

    # Verificar si la contraseña es correcta (si tienes un campo para almacenar contraseñas)
    # Aquí se asume que tienes una función para validar contraseñas (similar a los usuarios)
    # if not restaurante.check_password(password):
    #    return jsonify({'msg': 'Contraseña incorrecta'}), 401

    # Generar el Access Token y Refresh Token
    access_token = create_access_token(identity=restaurante.id)
    refresh_token = create_refresh_token(identity=restaurante.id)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200


# Obtener todos los restaurantes (GET /restaurantes)
@api.route('/restaurantes', methods=['GET'])
def get_all_restaurantes():
    restaurantes = Restaurantes.query.all()
    return jsonify([restaurante.serialize() for restaurante in restaurantes]), 200

# Obtener un restaurante por su ID (GET /restaurantes/<int:restaurante_id>)
@api.route('/restaurantes/<int:restaurante_id>', methods=['GET'])
def get_restaurante(restaurante_id):
    restaurante = Restaurantes.query.get(restaurante_id)
    if not restaurante:
        return jsonify({'msg': 'Restaurante no encontrado'}), 404

    return jsonify(restaurante.serialize()), 200

# Actualizar un restaurante (PUT /restaurantes/<int:restaurante_id>)
@api.route('/restaurantes/<int:restaurante_id>', methods=['PUT'])
@jwt_required()  # Sólo los profesionales pueden actualizar los restaurantes
def update_restaurante(restaurante_id):
    body = request.get_json()
    restaurante = Restaurantes.query.get(restaurante_id)

    if not restaurante:
        return jsonify({'msg': 'Restaurante no encontrado'}), 404

    # Actualizar los campos del restaurante
    restaurante.nombre = body.get('nombre', restaurante.nombre)
    restaurante.email = body.get('email', restaurante.email)
    restaurante.direccion = body.get('direccion', restaurante.direccion)
    restaurante.latitud = body.get('latitud', restaurante.latitud)
    restaurante.longitud = body.get('longitud', restaurante.longitud)
    restaurante.telefono = body.get('telefono', restaurante.telefono)
    restaurante.cubiertos = body.get('cubiertos', restaurante.cubiertos)
    restaurante.franja_horaria = body.get('franja_horaria', restaurante.franja_horaria)
    restaurante.reservas_por_dia = body.get('reservas_por_dia', restaurante.reservas_por_dia)
    restaurante.valoracion = body.get('valoracion', restaurante.valoracion)
    restaurante.categorias_id = body.get('categorias_id', restaurante.categorias_id)

    db.session.commit()

    return jsonify({'msg': 'Restaurante actualizado con éxito'}), 200

# Eliminar un restaurante (DELETE /restaurantes/<int:restaurante_id>)
@api.route('/restaurantes/<int:restaurante_id>', methods=['DELETE'])
@jwt_required()  # Sólo los profesionales pueden eliminar los restaurantes
def delete_restaurante(restaurante_id):
    restaurante = Restaurantes.query.get(restaurante_id)

    if not restaurante:
        return jsonify({'msg': 'Restaurante no encontrado'}), 404

    db.session.delete(restaurante)
    db.session.commit()

    return jsonify({'msg': 'Restaurante eliminado con éxito'}), 200

#CREAR RESERVA

@api.route('/usuario/reservas', methods=['POST'])
@jwt_required()
def crear_reserva():
    print("hola")

    body = request.get_json()
    usuario_id = get_jwt_identity()
    restaurante_id = body.get('restaurante_id')
    fecha_reserva = body.get('fecha_reserva')
    adultos = body.get('adultos')
    niños = body.get('niños')
    trona= body.get('trona')

    if not all([restaurante_id, fecha_reserva, adultos, niños, trona]):
        return jsonify({"error": "Faltan datos para crear la reserva"}), 400

    nueva_reserva = Reserva(
        user_id=usuario_id,
        restaurante_id=restaurante_id,
        fecha_reserva=fecha_reserva,
        adultos=adultos,
        niños=niños,
        trona=trona,
    )
    db.session.add(nueva_reserva)
    db.session.commit()
    
    return jsonify({"message": "Reserva creada con éxito", "reserva": nueva_reserva.serialize()}), 201

#OBTENER RESERVA

@api.route('/usuario/<int:user_id>/reservas', methods=['GET'])
def obtener_reservas_usuario(user_id):
    reservas = Reserva.query.filter_by(user_id=user_id).all()
    reservas_serializadas = list(map(lambda r: r.serialize(), reservas))
    
    return jsonify(reservas_serializadas), 200

#ACTUALIZAR RESERVA

@api.route('/reservas/<int:reserva_id>', methods=['PUT'])
def actualizar_reserva(reserva_id):
    body = request.get_json()
    
    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"error": "Reserva no encontrada"}), 404

    if 'fecha_reserva' in body:
        reserva.fecha_reserva = body['fecha_reserva']
    if 'numero_personas' in body:
        reserva.numero_personas = body['numero_personas']

    db.session.commit()
    
    return jsonify({"message": "Reserva actualizada con éxito", "reserva": reserva.serialize()}), 200

#BORRAR RESERVA

@api.route('/reservas/<int:reserva_id>', methods=['DELETE'])
def cancelar_reserva(reserva_id):
    reserva = Reserva.query.get(reserva_id)
    if not reserva:
        return jsonify({"error": "Reserva no encontrada"}), 404

    reserva.estado = "cancelada"
    db.session.commit()

    return jsonify({"message": "Reserva cancelada con éxito", "reserva": reserva.serialize()}), 200

#CREAR FAVORITOS

@api.route('/usuario/<int:usuario_id>/favoritos', methods=['POST'])
def agregar_favorito(usuario_id):

    body = request.json

    restaurante_id = body.get('restaurantes_id')

    if not usuario_id or not restaurante_id :
        return jsonify({"error": "Faltan datos para agregar a favoritos"}), 400

    favorito_existente = Restaurantes_Favoritos.query.filter_by(usuario_id=usuario_id, restaurantes_id=restaurante_id).first()
    if favorito_existente:
        return jsonify({"error": "El restaurante ya está en favoritos"}), 400

    nuevo_favorito = Restaurantes_Favoritos(usuario_id=usuario_id, restaurantes_id=restaurante_id)
    db.session.add(nuevo_favorito)
    db.session.commit()

    return jsonify({"message": "Restaurante agregado a favoritos", "favorito": nuevo_favorito.serialize()}), 201

#ELIMINAR FAVORITO

@api.route('/usuario/<int:usuario_id>/favoritos', methods=['DELETE'])
def eliminar_favorito(usuario_id):
    
    body = request.get_json()

    restaurantes_id = body.get('restaurantes_id')

    if not all([usuario_id, restaurantes_id]):
        return jsonify({"error": "Faltan datos para eliminar de favoritos"}), 400

    favorito = Restaurantes_Favoritos.query.filter_by(usuario_id=usuario_id, restaurantes_id=restaurantes_id).first()

    if not favorito:
        return jsonify({"error": "El restaurante no está en favoritos"}), 404

    db.session.delete(favorito)
    db.session.commit()

    return jsonify({"message": "Restaurante eliminado de favoritos"}), 200

#OBTENER FAVORITO

@api.route('/usuario/favoritos/<int:user_id>', methods=['GET'])
def obtener_favoritos(user_id):
    favoritos = Restaurantes_Favoritos.query.filter_by(usuario_id=user_id).all()
    all_favoritos = list(map(lambda x: x.serialize(), favoritos))
    
    return jsonify(all_favoritos), 200

#CREAR VALORACION

@api.route('/usuario/<int:user_id>/valoraciones', methods=['POST'])
def agregar_valoracion(user_id):
    body = request.get_json()

    restaurante_id = body.get('restaurante_id')
    puntuacion = body.get('puntuacion')
    comentario = body.get('comentario', "")

    if not all([user_id, restaurante_id, puntuacion]):
        return jsonify({"error": "Faltan datos para la valoración"}), 400

    valoracion_existente = Valoracion.query.filter_by(usuario_id=user_id, restaurante_id=restaurante_id).first()
    if valoracion_existente:
        return jsonify({"error": "Ya has valorado este restaurante"}), 400

    nueva_valoracion = Valoracion(
        usuario_id=user_id,
        restaurante_id=restaurante_id,
        puntuacion=puntuacion,
        comentario=comentario
    )
    
    db.session.add(nueva_valoracion)
    db.session.commit()

    return jsonify({"message": "Valoración creada con éxito", "valoracion": nueva_valoracion.serialize()}), 201

#ACTUALIZAR VALORACION

@api.route('/usuario/<int:user_id>/valoraciones', methods=['PUT'])
def actualizar_valoracion(user_id):
    body = request.get_json()

    restaurante_id = body.get('restaurante_id')
    puntuacion = body.get('puntuacion')
    comentario = body.get('comentario', "")

    if not all([user_id, restaurante_id, puntuacion]):
        return jsonify({"error": "Faltan datos para poder actualizar la valoración"}), 400

    valoracion_existente = Valoracion.query.filter_by(usuario_id=user_id, restaurante_id=restaurante_id).first()
    if not valoracion_existente:
        return jsonify({"error": "No se encontró ninguna valoración para este restaurante hecha por este usuario"}), 404

    valoracion_existente.puntuacion = puntuacion
    valoracion_existente.comentario = comentario
    db.session.commit()

    return jsonify({"message": "Valoración actualizada con éxito", "valoracion": valoracion_existente.serialize()}), 200

#BORRAR VALORACION

@api.route('/usuario/<int:user_id>/valoraciones', methods=['DELETE'])
def eliminar_valoracion(user_id):
    body = request.get_json()

    restaurante_id = body.get('restaurante_id')

    if not all([user_id, restaurante_id]):
        return jsonify({"error": "Faltan datos para  poder eliminar la valoración"}), 400

    valoracion = Valoracion.query.filter_by(usuario_id=user_id, restaurante_id=restaurante_id).first()

    if not valoracion:
        return jsonify({"error": "No existe una valoración para este restaurante"}), 404

    db.session.delete(valoracion)
    db.session.commit()

    return jsonify({"message": "Valoración eliminada con éxito"}), 200

#OBTENER VALORACION

@api.route('/restaurante/<int:restaurante_id>/valoracion', methods=['GET'])
def obtener_valoracion_restaurante(restaurante_id):
    valoraciones = Valoracion.query.filter_by(restaurante_id=restaurante_id).all()
    
    if not valoraciones:
        return jsonify({"message": "Este restaurante no tiene valoraciones"}), 200
    
    all_valoraciones = list(map(lambda x: x.serialize(), valoraciones))
    
    return jsonify(all_valoraciones), 200

#PROMEDIAR VALORACIONES

@api.route('/restaurante/<int:restaurante_id>/valoracion_promedio', methods=['GET'])
def obtener_valoracion_promedio(restaurante_id):
    valoraciones = Valoracion.query.filter_by(restaurante_id=restaurante_id).all()

    if not valoraciones:
        return jsonify({"message": "Este restaurante no tiene valoraciones"}), 200

    total_valoraciones = sum([valoracion.puntuacion for valoracion in valoraciones])
    promedio = total_valoraciones / len(valoraciones)

    return jsonify({"restaurante_id": restaurante_id, "promedio_valoracion": promedio}), 200

#Cloudinary
@api.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        # Obtener la imagen del formulario (request.files)
        image = request.files['file']  #Frontend debe enviar el archivo correctamente
         # Subir la imagen a Cloudinary
        upload_result = cloudinary.uploader.upload(image)
        # Devolver la URL de la imagen subida
        return jsonify({
            "msg": "Imagen subida con éxito",
            "url": upload_result['secure_url']}), 200
    except Exception as e:
        return jsonify({"msg": "Error subiendo la imagen", "error": str(e)}), 400
    

@api.route('/poblar_restaurantes', methods=['POST'])
def poblar_restaurante():
    try:
        mockRestaurants = [
        { "id": 1, "nombre": "Trattoria Bella", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 1, "direccion": "Calle Mayor 45, Madrid", "valoracion": 4.7,  "image": "https://i0.wp.com/travelandleisure-es.com/wp-content/uploads/2024/04/TAL-ristorante-seating-ITLNRESTAURANTS0424-5403b234cdbd4026b2e98bed659b1634.webp?fit=750%2C500&ssl=1" },
        { "id": 2, "nombre": "Pasta Fresca", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 1, "direccion": "Calle de la Paz 10, Valencia", "valoracion": 4.3,  "image": "https://static.wixstatic.com/media/e7e925_6e8c1ffb4cd8432ea5a37cec591048ad~mv2.jpg/v1/fill/w_2880,h_1598,al_c,q_90,usm_0.66_1.00_0.01,enc_auto/e7e925_6e8c1ffb4cd8432ea5a37cec591048ad~mv2.jpg" },
        { "id": 3, "nombre": "Osteria del Mare", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 1, "direccion": "Paseo Marítimo 8, Barcelona", "valoracion": 4.5,  "image": "https://s3.abcstatics.com/abc/www/multimedia/gastronomia/2023/01/16/forneria-RMj62LyNsJZlBCufEion5YK-1200x840@abc.jpg" },
        { "id": 4, "nombre": "El Mariachi Loco", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 2, "direccion": "Avenida de América 23, Madrid", "valoracion": 4.6,  "image": "https://i0.wp.com/lattin.ca/wp-content/uploads/2016/05/El_Catrin_Inside_51.png?w=1085&ssl=1" },
        { "id": 5, "nombre": "Cantina del Cactus", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 2, "direccion": "Boulevard de los Aztecas 15, Barcelona", "valoracion": 4.2,  "image": "https://images.ecestaticos.com/kCk1Qljo-a1ll2eVt2ovDfRo7pY=/0x0:1885x900/1200x900/filters:fill(white):format(jpg)/f.elconfidencial.com%2Foriginal%2Fc66%2Fa99%2F8d5%2Fc66a998d5952c07d264a23dfdbecdcf2.jpg" },
        { "id": 6, "nombre": "Tacos y Más", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 2, "direccion": "Calle del Carmen 99, Valencia", "valoracion": 4.7,  "image": "https://www.lavanguardia.com/files/image_990_484/files/fp/uploads/2022/08/04/62ebd8920f8fe.r_d.3275-3425-1343.jpeg" },
        { "id": 7, "nombre": "Sakura House", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 3, "direccion": "Calle Bonsai 12, Madrid", "valoracion": 4.8,  "image": "https://winegogh.es/wp-content/uploads/2024/08/kelsen-fernandes-2hEcc-4cwZA-unsplash-scaled.jpg" },
        { "id": 8, "nombre": "Samurai Sushi", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 3, "direccion": "Avenida de Japón 23, Barcelona", "valoracion": 4.6,  "image": "https://imagenes.esdiario.com/files/image_990_660/uploads/2024/06/22/66765b6b14a50.jpeg" },
        { "id": 9, "nombre": "Yoko Ramen", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 3, "direccion": "Calle del Pescador 7, Valencia", "valoracion": 4.4,  "image": "https://media.timeout.com/images/100614777/1536/864/image.webp" },
        { "id": 10, "nombre": "Dragón Rojo", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 4, "direccion": "Calle Pagoda 34, Madrid", "valoracion": 4.5,  "image": "https://offloadmedia.feverup.com/valenciasecreta.com/wp-content/uploads/2022/01/13123703/restaurantes-chinos-valencia-1024x683.jpg" },
        { "id": 11, "nombre": "Dim Sum Palace", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 4, "direccion": "Avenida Oriente 22, Barcelona", "valoracion": 4.3,  "image": "https://offloadmedia.feverup.com/valenciasecreta.com/wp-content/uploads/2022/01/13123704/277526606_706703347177521_4948663648545209465_n.jpg" },
        { "id": 12, "nombre": "Pekin Express", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 4, "direccion": "Calle Muralla 8, Sevilla", "valoracion": 4.2,  "image": "https://www.lavanguardia.com/files/image_990_484/uploads/2020/01/15/5e9977269a0d4.jpeg" },
        { "id": 13, "nombre": "Curry Masala", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 5, "direccion": "Calle Taj Mahal 12, Madrid", "valoracion": 4.6,  "image": "https://www.sentirsebiensenota.com/wp-content/uploads/2022/04/restaurantes-indios-valencia-1080x640.jpg" },
        { "id": 14, "nombre": "Palacio del Sabor", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 5, "direccion": "Avenida Ganges 5, Valencia", "valoracion": 4.4,  "image": "https://tumediodigital.com/wp-content/uploads/2021/03/comida-india-valencia.jpg" },
        { "id": 15, "nombre": "Namaste India", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 5, "direccion": "Boulevard Raj 10, Barcelona", "valoracion": 4.7,  "image": "https://phantom-elmundo.unidadeditorial.es/7279f37ebecb49cf7738402f76486caa/crop/0x0/1478x985/resize/746/f/webp/assets/multimedia/imagenes/2021/06/15/16237493606773.png" },
        { "id": 16, "nombre": "Hard Rock", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 6, "direccion": "Avenida de la Libertad 45, Madrid", "valoracion": 4.2,  "image": "https://ibiza-spotlight1.b-cdn.net/sites/default/files/styles/embedded_auto_740_width/public/article-images/138583/embedded-1901415944.jpeg?itok=oWiIVuDP" },
        { "id": 17, "nombre": "Steak House", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 6, "direccion": "Calle Ruta 66 77, Barcelona", "valoracion": 4.5,  "image": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/17/34/e2/7d/barbecued-pork-ribs.jpg?w=1200&h=-1&s=1" },
        { "id": 18, "nombre": "Bernie's Diner", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 6, "direccion": "Calle Manhattan 23, Valencia", "valoracion": 4.3,  "image": "https://offloadmedia.feverup.com/barcelonasecreta.com/wp-content/uploads/2015/07/09112834/usa-2.jpg" },
        { "id": 19, "nombre": "Taberna Flamenca", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 7, "direccion": "Calle Sevilla 7, Sevilla", "valoracion": 4.6,  "image": "https://s1.ppllstatics.com/hoy/www/multimedia/202111/13/media/cortadas/165813563--1968x1310.jpg" },
        { "id": 20, "nombre": "Casa del Arroz", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 7, "direccion": "Paseo de la Castellana 12, Madrid", "valoracion": 4.4,  "image": "https://ibiza-spotlight1.b-cdn.net/sites/default/files/styles/embedded_auto_740_width/public/article-images/138301/embedded-1808145593.jpg?itok=06R4cJZd" },
        { "id": 21, "nombre": "Sabores del Mar", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 7, "direccion": "Plaza del Mar 3, Barcelona", "valoracion": 4.5, "image": "https://imagenes.elpais.com/resizer/v2/D7EEJHYCERGLVFSCY43QPDLO6E.jpg?auth=0dbf855b68440ee29905c103edef7d7cc1add094e50abbc376b2494772c44dd9&width=1200" },
        { "id": 22, "nombre": "Oasis del Sabor", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 8, "direccion": "Calle del Desierto 14, Granada", "valoracion": 4.6,  "image": "https://www.sientemarruecos.viajes/wp-content/uploads/2019/10/El-Restaurante-Al-Mounia-es-un-restaurante-marroqu%C3%AD-en-Madrid.jpg" },
        { "id": 23, "nombre": "El Sultán", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 8, "direccion": "Avenida Oasis 18, Córdoba", "valoracion": 4.5,  "image": "https://www.guiarepsol.com/content/dam/repsol-guia/contenidos-imagenes/comer/nuestros-favoritos/restaurante-el-califa-(vejer,-c%C3%A1diz)/00El_Califa_.jpg" },
        { "id": 24, "nombre": "Mezze Lounge", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 8, "direccion": "Boulevard Dubai 25, Madrid", "valoracion": 4.7,  "image": "https://marruecoshoy.com/wp-content/uploads/2021/09/chebakia.png" },
        { "id": 25, "nombre": "Bangkok Delight", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 9, "direccion": "Calle Siam 4, Barcelona", "valoracion": 4.4,  "image": "https://viajeatailandia.com/wp-content/uploads/2018/07/Restaurantes-Tailandia.jpg" },
        { "id": 26, "nombre": "Sabai Sabai", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 9, "direccion": "Avenida Phuket 21, Madrid", "valoracion": 4.5,  "image": "https://www.topasiatour.com/pic/thailand/city/Bangkok/guide/jianxing-restaurant.jpg" },
        { "id": 27, "nombre": "Thai Spice", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 9, "direccion": "Boulevard Chiang Mai 8, Valencia", "valoracion": 4.7,  "image": "https://www.hola.com/imagenes/viajes/2015030677296/bares-restaurantes-rascacielos-bangkok-tailandia/0-311-16/a_Sirocco---interior-a.jpg" },
        { "id": 28, "nombre": "Haller", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 10, "direccion": "Avenida Montmartre 9, Barcelona", "valoracion": 4.7,  "image": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/0c/f8/0d/4d/arbol-de-yuca.jpg?w=2400&h=-1&s=1" },
        { "id": 29, "nombre": "Sublimotion", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 10, "direccion": "Paseo de la Castellana 13, Madrid", "valoracion": 4.6,  "image": "https://www.economistjurist.es/wp-content/uploads/sites/2/2023/08/293978.jpeg" },
        { "id": 30, "nombre": "Chez Marie", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 10, "direccion": "Calle Napoleón 19, Valencia", "valoracion": 4.5,  "image": "https://6e131064.rocketcdn.me/wp-content/uploads/2022/08/Girafe%C2%A9RomainRicard-5-1100x650-1.jpeg" },
        { "id": 31, "nombre": "Asador Don Julio", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 11, "direccion": "Calle de la Carne 9, Madrid", "valoracion": 4.7,  "image": "https://media.timeout.com/images/106116523/1536/864/image.webp" },
        { "id": 32, "nombre": "Casa del Fernet", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 11, "direccion": "Paseo Marítimo 11, Barcelona", "valoracion": 4.6,  "image": "https://rio-marketing.com/wp-content/uploads/2024/02/fernet1.webp" },
        { "id": 33, "nombre": "Empanadas Locas", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 11, "direccion": "Calle de Verdad 19, Valencia", "valoracion": 4.5,  "image": "https://cdn.inteligenciaviajera.com/wp-content/uploads/2019/11/comida-tipica-argentina.jpg" },
        { "id": 34, "nombre": "Green Delight", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 12, "direccion": "Avenida de la Paz 45, Madrid", "valoracion": 4.7,  "image": "https://menusapiens.com/wp-content/uploads/2017/04/Comida-Sana-Alta-Cocina-MenuSapiens.jpeg" },
        { "id": 35, "nombre": "Vida Verde", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 12, "direccion": "Calle de la Luna 8, Barcelona", "valoracion": 4.6,  "image": "https://imagenes.elpais.com/resizer/v2/BSUD6VP76FGXJJE75BHINHYRAY.jpg?auth=2b94a0b2cdda6a164ea7b90ff96035281c2cd1ae8ead08a9d6d24df0d8ad9882&width=1200" },
        { "id": 36, "nombre": "Hortaliza Viva", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 12, "direccion": "Calle Mayor 21, Valencia", "valoracion": 4.5,  "image": "https://blog.covermanager.com/wp-content/uploads/2024/05/Como-Crear-un-Menu-Sostenible-para-Restaurantes-2048x1365.jpg" },
        { "id": 37, "nombre": "Sabor Latino", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 13, "direccion": "Calle de Alcalá 22, Madrid", "valoracion": 4.7,  "image": "https://www.clarin.com/img/2021/06/03/_32tg_291_1256x620__1.jpg" },
        { "id": 38, "nombre": "El Fogón de la Abuela", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 13, "direccion": "Calle de la Reina 15, Barcelona", "valoracion": 4.6,  "image": "https://jotajotafoods.com/wp-content/uploads/2022/05/plato-Bandeja-Paisa.jpg" },
        { "id": 39, "nombre": "Casa Caribe", "telefono": "555-555-555", "email": "reataurante@gmail.com", "cantidad_mesas": 10, "categoria_id": 13, "direccion": "Paseo de la Castellana 33, Valencia", "valoracion": 4.5,  "image": "https://theobjective.com/wp-content/uploads/2024/04/2022-09-02.webp" }
    ]
        for restaurante in mockRestaurants:
            nuevo_restaurante = Restaurantes(

                nombre=restaurante['nombre'],
                email=restaurante['email'],
                direccion=restaurante['direccion'],
                telefono=restaurante['telefono'],
                cantidad_mesas=restaurante['cantidad_mesas']
            )

            db.session.add(nuevo_restaurante)

        db.session.commit() 
        
        return jsonify({"mensaje": "Restaurantes cargados a la base de datos con éxito"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    