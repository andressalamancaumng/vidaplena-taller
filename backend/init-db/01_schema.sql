-- VidaPlena — Red de Clínicas (esquema y datos de ejemplo, TODO ficticio)
-- Seguridad Informática, UMNG — Sesión 7

CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    cedula VARCHAR(255) NOT NULL,
    cedula_indice CHAR(64) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(150),
    contrasena VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios_admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL UNIQUE,
    contrasena VARCHAR(255) NOT NULL,
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

-- Guardar solo la identidad de cada sesión permite revocarla sin almacenar el JWT.
CREATE TABLE IF NOT EXISTS sesiones (
    id CHAR(64) PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    expira DATETIME NOT NULL,
    INDEX idx_sesion_expira (expira)
);

-- Comprueba que los reinicios reutilicen las llaves originales, sin guardarlas aquí.
CREATE TABLE IF NOT EXISTS seguridad_estado (
    id TINYINT PRIMARY KEY,
    comprobante VARCHAR(255) NOT NULL,
    indice_comprobante CHAR(64) NOT NULL
);

-- app/datos_demo.py inserta los ejemplos ya cifrados y con hashes bcrypt.
