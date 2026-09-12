"""
seed.py

Sembrado de datos de demostración para VidaPlena.

En la versión original del taller, los datos de ejemplo se insertaban
directamente en `init-db/01_schema.sql` con contraseñas y cédulas en texto
plano (Falla 4 y Falla 5). En la solución de referencia, el sembrado se
traslada a la aplicación porque requiere aplicar hashing (bcrypt) y cifrado
(Fernet) — algo que SQL puro no puede hacer. Se ejecuta una sola vez, al
arrancar la API (ver `@app.on_event("startup")` en main.py), y solo si las
tablas están vacías, para no duplicar datos en reinicios sucesivos del
contenedor.

Los datos, nombres y cifras son 100% ficticios (mismos usados desde la
Sesión 7).
"""

from app.database import obtener_conexion
from app import security


def _tabla_vacia(cursor, tabla: str) -> bool:
    cursor.execute(f"SELECT COUNT(*) AS total FROM {tabla}")
    return cursor.fetchone()["total"] == 0


def sembrar_datos_demo() -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        if not _tabla_vacia(cursor, "pacientes"):
            # Ya hay datos (contenedor reiniciado, no primera vez): no sembrar de nuevo.
            return

        pacientes_demo = [
            ("Ana Ficticia Pérez", "1010023456", "3011234567", "ana.ficticia@correoejemplo.co", "Cl4veSegura123"),
            ("Carlos Ejemplo Gómez", "1015098765", "3109876543", "carlos.ejemplo@correoejemplo.co", "MiPerro2019"),
            ("Laura Modelo Rodríguez", "1022334455", "3201122334", "laura.modelo@correoejemplo.co", "12345678"),
        ]

        ids_pacientes = []
        for nombre, cedula, telefono, correo, contrasena in pacientes_demo:
            cursor.execute(
                """
                INSERT INTO pacientes (nombre, cedula, cedula_hash, telefono, correo, contrasena_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    security.encrypt_value(cedula),
                    security.hash_lookup(cedula),
                    telefono,
                    correo,
                    security.hash_password(contrasena),
                ),
            )
            ids_pacientes.append(cursor.lastrowid)

        cursor.execute(
            """
            INSERT INTO usuarios_admin (usuario, contrasena_hash, rol)
            VALUES (%s, %s, %s)
            """,
            ("admin", security.hash_password("Admin123!"), "administrador"),
        )

        citas_demo = [
            (ids_pacientes[0], "2026-09-10", "09:00:00", "Dra. Valentina Ríos", "Control anual",
             "Paciente sana, sin hallazgos relevantes."),
            (ids_pacientes[1], "2026-09-11", "10:30:00", "Dr. Mateo Salazar", "Dolor abdominal",
             "Sospecha de gastritis, se ordenan exámenes."),
            (ids_pacientes[2], "2026-09-12", "14:00:00", "Dra. Valentina Ríos", "Consulta psicológica",
             "Episodio de ansiedad, se remite a psicología."),
        ]
        for paciente_id, fecha, hora, medico, motivo, diagnostico in citas_demo:
            cursor.execute(
                """
                INSERT INTO citas (paciente_id, fecha, hora, medico, motivo_consulta, diagnostico)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (paciente_id, fecha, hora, medico, motivo, security.encrypt_value(diagnostico)),
            )

        facturas_demo = [
            (ids_pacientes[0], "Consulta general", 80000.00, "pagado", 0),
            (ids_pacientes[1], "Exámenes de laboratorio", 250000.00, "pendiente", 15),
            (ids_pacientes[2], "Consulta psicológica", 120000.00, "pendiente", 45),
        ]
        for paciente_id, servicio, valor, estado_pago, dias_mora in facturas_demo:
            cursor.execute(
                """
                INSERT INTO facturas (paciente_id, servicio, valor, estado_pago, dias_mora)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (paciente_id, servicio, valor, estado_pago, dias_mora),
            )

        conexion.commit()
        print("[seed] Datos de demostración sembrados correctamente.")
    finally:
        cursor.close()
        conexion.close()
