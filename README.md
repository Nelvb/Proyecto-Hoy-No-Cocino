# ¡Hoy No Cocino!

¡Hoy No Cocino! es una aplicación web para la gestión de reservas en restaurantes, facilitando tanto la reserva de mesas por parte de los usuarios como la administración de detalles por los propios restaurantes. Este proyecto fue desarrollado como parte del curso Full Stack Developer en 4Geeks Academy.

## Tecnologías Utilizadas

### 🛠️ Stack
- **Frontend**: React.js, JavaScript, HTML5, CSS3
- **Backend**: Flask, Python
- **Bases de Datos**: PostgreSQL, SQLAlchemy
- **Autenticación y Seguridad**: JWT (JSON Web Tokens)
- **Gestión de Imágenes**: Cloudinary
- **Notificaciones y Correos Electrónicos**: Flask-Mail

## Funcionalidades Principales

- **Registro y Autenticación**: Permite a los usuarios registrarse y acceder de manera segura.
- **Reservas**: Los usuarios pueden buscar restaurantes, ver disponibilidad, y realizar reservas online.
- **Área Privada para Restaurantes**: Gestión de disponibilidad, detalles de mesas y configuración de horarios.
- **Envío de Confirmaciones por Correo**: Los usuarios reciben confirmación de sus reservas directamente en su correo.
- **Sistema de Favoritos**: Los usuarios pueden marcar restaurantes como favoritos.

## Instalación

1. **Backend**: Requiere Python 3.8+, Pipenv, y una base de datos PostgreSQL.
    ```bash
    $ pipenv install
    $ cp .env.example .env
    ```
   Configura la base de datos en el archivo `.env` con la variable `DATABASE_URL` adecuada.

2. **Migración y Arranque de la Aplicación**
    ```bash
    $ pipenv run migrate
    $ pipenv run upgrade
    $ pipenv run start
    ```

3. **Frontend**: Requiere Node.js (versión 14+).
    ```bash
    $ npm install
    $ npm run start
    ```

## Despliegue

La aplicación está lista para desplegarse en servicios como Render o Heroku. Sigue la [documentación oficial](https://start.4geeksacademy.com/deploy).

## Contribuyentes

Este proyecto fue creado como parte del bootcamp en [4Geeks Academy](https://4geeksacademy.com).

---
