import bcrypt
from app import database

conexion = database.obtener_conexion()
cursor = conexion.cursor()

for tabla, columna_id in [('pacientes', 'id'), ('usuarios_admin', 'id')]:
    cursor.execute(f"SELECT {columna_id}, contrasena FROM {tabla}")
    filas = cursor.fetchall()
    
    for fila_id, contrasena in filas:
        if not contrasena.startswith('$2b$'):
            nuevo_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(f"UPDATE {tabla} SET contrasena = %s WHERE {columna_id} = %s", (nuevo_hash, fila_id))
            print(f"{tabla} id={fila_id}: migrado")

conexion.commit()
cursor.close()
conexion.close()
print("¡Migración completada con éxito!")