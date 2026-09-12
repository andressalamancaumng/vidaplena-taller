from app import database
import bcrypt

conexion = database.obtener_conexion()
cursor = conexion.cursor()

cursor.execute("SELECT id, contrasena FROM pacientes")
filas = cursor.fetchall()

for fila in filas:
    id_paciente = fila[0]
    contrasena_actual = fila[1]
    nuevo_hash = bcrypt.hashpw(contrasena_actual.encode(), bcrypt.gensalt())
    cursor.execute(
        "UPDATE pacientes SET contrasena = %s WHERE id = %s",
        (nuevo_hash, id_paciente),
    )

conexion.commit()
cursor.close()
conexion.close()

print("Migración completada: todas las contraseñas fueron convertidas a hash.")