/**
 * URL base de la API de VidaPlena.
 *
 * Con docker-compose, el backend queda expuesto en el puerto 8000 del
 * propio computador (localhost), así que el navegador puede llamarlo
 * directamente sin necesidad de un proxy inverso.
 *
 * Si despliegan esto en una máquina de AWS (ver la guía opcional en
 * docs/), cambien este valor por la URL pública del backend, por ejemplo:
 *   export const API_URL = 'http://<ip-publica-ec2>:8000/api';
 */
export const API_URL = 'http://localhost:8000/api';
