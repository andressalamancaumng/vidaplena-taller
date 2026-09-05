-- VidaPlena — Red de Clínicas (esquema y datos de ejemplo, TODO ficticio)
-- Seguridad Informática, UMNG — Sesión 7

CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    cedula VARCHAR(20) NOT NULL UNIQUE,
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

-- Datos de ejemplo, 100% ficticios (mismos nombres usados en el laboratorio anterior)
INSERT INTO pacientes (nombre, cedula, telefono, correo, contrasena) VALUES
('Ana Ficticia Pérez', '1010023456', '3011234567', 'ana.ficticia@correoejemplo.co', 'Cl4veSegura123'),
('Carlos Ejemplo Gómez', '1015098765', '3109876543', 'carlos.ejemplo@correoejemplo.co', 'MiPerro2019'),
('Laura Modelo Rodríguez', '1022334455', '3201122334', 'laura.modelo@correoejemplo.co', '12345678');

INSERT INTO usuarios_admin (usuario, contrasena, rol) VALUES
('admin', 'Admin123!', 'administrador');

INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) VALUES
(1, '2026-09-10', '09:00:00', 'Dra. Valentina Ríos', 'Control anual', 'Paciente sana, sin hallazgos relevantes.'),
(2, '2026-09-11', '10:30:00', 'Dr. Mateo Salazar', 'Dolor abdominal', 'Sospecha de gastritis, se ordenan exámenes.'),
(3, '2026-09-12', '14:00:00', 'Dra. Valentina Ríos', 'Consulta psicológica', 'Episodio de ansiedad, se remite a psicología.');

INSERT INTO facturas (paciente_id, servicio, valor, estado_pago, dias_mora) VALUES
(1, 'Consulta general', 80000.00, 'pagado', 0),
(2, 'Exámenes de laboratorio', 250000.00, 'pendiente', 15),
(3, 'Consulta psicológica', 120000.00, 'pendiente', 45);
