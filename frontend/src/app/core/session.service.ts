import { Injectable } from '@angular/core';

/**
 * Manejo de "sesión" en el cliente.
 *
 * ⚠️ Nota pedagógica: esto es deliberadamente simple. Guardamos los datos
 * del paciente/administrador que inició sesión en localStorage, pero el
 * backend (ver /api/admin/pacientes en la API) NO verifica en absoluto que
 * quien llama esté autenticado. Es decir: esta "sesión" solo sirve para que
 * la interfaz muestre u oculte botones — no protege realmente los datos.
 * Encontrar y corregir esa diferencia es parte del taller.
 */

export interface PacienteSesion {
  tipo: 'paciente';
  id: number;
  nombre: string;
  cedula: string;
  token: string;
}

export interface AdminSesion {
  tipo: 'admin';
  id: number;
  usuario: string;
  rol: string;
  token: string;
}

export type Sesion = PacienteSesion | AdminSesion;

const CLAVE_STORAGE = 'vidaplena_sesion';

@Injectable({ providedIn: 'root' })
export class SessionService {
  guardarSesion(sesion: Sesion): void {
    localStorage.setItem(CLAVE_STORAGE, JSON.stringify(sesion));
  }

  obtenerSesion(): Sesion | null {
    const crudo = localStorage.getItem(CLAVE_STORAGE);
    return crudo ? (JSON.parse(crudo) as Sesion) : null;
  }

  esAdmin(): boolean {
    return this.obtenerSesion()?.tipo === 'admin';
  }

  cerrarSesion(): void {
    localStorage.removeItem(CLAVE_STORAGE);
  }
}
