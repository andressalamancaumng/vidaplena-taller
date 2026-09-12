-- VidaPlena — Red de Clínicas (esquema)
-- Seguridad Informática, UMNG — Sesión 7 / Solución de referencia Sesión 8

-- NOTA (solución de referencia): los datos de ejemplo ya NO se insertan aquí
-- mediante SQL plano. Se sembraron originalmente con contraseñas y cédulas en
-- texto claro (Falla 4 y Falla 5). Ahora el sembrado se hace en tiempo de
-- arranque desde la aplicación (ver backend/app/seed.py), porque requiere
-- aplicar hashing (bcrypt) y cifrado (Fernet) — operaciones que SQL puro no
-- puede realizar.

CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    cedula VARCHAR(255) NOT NULL,
    cedula_hash CHAR(64) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(150),
    contrasena_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios_admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'administrador'
);

CREATE TABLE IF NOT EXISTS citas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    medico VARCHAR(150) NOT NULL,
    motivo_consulta VARCHAR(255),
    diagnostico TEXT,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
);

CREATE TABLE IF NOT EXISTS facturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    servicio VARCHAR(150) NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    estado_pago VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    dias_mora INT DEFAULT 0,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
);
