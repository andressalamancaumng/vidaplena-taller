"""
Migración única: cifra las cédulas de pacientes y los diagnósticos de
citas que ya existían en texto plano antes del Hallazgo 5.

Ejecutar UNA sola vez, dentro del contenedor del backend:
    docker compose exec backend python -m app.migrar_cifrado
"""

from app import database
from cryptography.fernet import Fernet

CLAVE_CIFRADO = b'4kL9pXz2Vb8sQ1rT6yU3wA7cE0mN5hJ8oI2dF4gK9qY='
cifrador = Fernet(CLAVE_CIFRADO)

conexion = database.obtener_conexion()
cursor = conexion.cursor()

# Cédulas de pacientes
cursor.execute("SELECT id, cedula FROM pacientes")
pacientes = cursor.fetchall()
for id_paciente, cedula in pacientes:
    nueva = cifrador.encrypt(cedula.encode()).decode()
    cursor.execute("UPDATE pacientes SET cedula = %s WHERE id = %s", (nueva, id_paciente))

# Diagnósticos de citas (pueden ser NULL)
cursor.execute("SELECT id, diagnostico FROM citas WHERE diagnostico IS NOT NULL")
citas = cursor.fetchall()
for id_cita, diagnostico in citas:
    nuevo = cifrador.encrypt(diagnostico.encode()).decode()
    cursor.execute("UPDATE citas SET diagnostico = %s WHERE id = %s", (nuevo, id_cita))

conexion.commit()
cursor.close()
conexion.close()

print(f"Migración de cifrado completada: {len(pacientes)} cédulas y {len(citas)} diagnósticos cifrados.")