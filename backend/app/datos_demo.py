"""Ejemplos SINTÉTICOS del taller: estas credenciales públicas no son aptas para producción."""

from app.seguridad import cifrar, hash_contrasena, indice_cedula


def cargar_demo(cursor):
    pacientes = [
        ("Ana Ficticia Pérez", "1010023456", "3011234567", "ana.ficticia@correoejemplo.co", "Cl4veSegura123"),
        ("Carlos Ejemplo Gómez", "1015098765", "3109876543", "carlos.ejemplo@correoejemplo.co", "MiPerro2019"),
        ("Laura Modelo Rodríguez", "1022334455", "3201122334", "laura.modelo@correoejemplo.co", "12345678"),
    ]
    ids = []
    for nombre, cedula, telefono, correo, contrasena in pacientes:
        cursor.execute(
            "INSERT INTO pacientes (nombre, cedula, cedula_indice, telefono, correo, contrasena) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nombre, cifrar(cedula, "pacientes.cedula"), indice_cedula(cedula),
             telefono, correo, hash_contrasena(contrasena)),
        )
        ids.append(cursor.lastrowid)
    cursor.execute(
        "INSERT INTO usuarios_admin (usuario, contrasena, rol) VALUES (%s, %s, %s)",
        ("admin", hash_contrasena("Admin123!"), "administrador"),
    )
    citas = [
        (ids[0], "2026-09-10", "09:00:00", "Dra. Valentina Ríos", "Control anual",
         "Paciente sana, sin hallazgos relevantes."),
        (ids[1], "2026-09-11", "10:30:00", "Dr. Mateo Salazar", "Dolor abdominal",
         "Sospecha de gastritis, se ordenan exámenes."),
        (ids[2], "2026-09-12", "14:00:00", "Dra. Valentina Ríos", "Consulta psicológica",
         "Episodio de ansiedad, se remite a psicología."),
    ]
    for paciente_id, fecha, hora, medico, motivo, diagnostico in citas:
        cursor.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (paciente_id, fecha, hora, medico, motivo, cifrar(diagnostico, "citas.diagnostico")),
        )
    cursor.executemany(
        "INSERT INTO facturas (paciente_id, servicio, valor, estado_pago, dias_mora) "
        "VALUES (%s, %s, %s, %s, %s)",
        [(ids[0], "Consulta general", 80000, "pagado", 0),
         (ids[1], "Exámenes de laboratorio", 250000, "pendiente", 15),
         (ids[2], "Consulta psicológica", 120000, "pendiente", 45)],
    )
