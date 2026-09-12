from app import database
from app.main import cifrar_dato, hash_busqueda, descifrar_dato

conexion = database.obtener_conexion()
cursor = conexion.cursor()

# 1. Cifrar las cédulas de los pacientes
cursor.execute("SELECT id, cedula FROM pacientes")
for pid, cedula in cursor.fetchall():
    try:
        descifrar_dato(cedula)
        continue  # Si ya estaba cifrada, la salta
    except Exception:
        pass

    cursor.execute(
        "UPDATE pacientes SET cedula = %s, cedula_hash = %s WHERE id = %s",
        (cifrar_dato(cedula), hash_busqueda(cedula), pid),
    )
    print(f"paciente {pid}: cedula cifrada")

# 2. Cifrar los diagnósticos de las citas
cursor.execute("SELECT id, diagnostico FROM citas WHERE diagnostico IS NOT NULL")
for cid, diagnostico in cursor.fetchall():
    try:
        descifrar_dato(diagnostico)
        continue  # Si ya estaba cifrado, lo salta
    except Exception:
        pass

    cursor.execute(
        "UPDATE citas SET diagnostico = %s WHERE id = %s",
        (cifrar_dato(diagnostico), cid),
    )
    print(f"cita {cid}: diagnostico cifrado")

conexion.commit()
cursor.close()
conexion.close()
print("¡Cifrado de datos completado con éxito!")
