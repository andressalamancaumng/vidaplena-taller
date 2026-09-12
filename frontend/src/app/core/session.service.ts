import { Injectable } from '@angular/core';

/** Estado en memoria: el servidor verifica el JWT y los permisos en cada petición. */
interface TokenSesion {
  access_token: string;
  expira_en: number;
}

export interface PacienteSesion extends TokenSesion {
  tipo: 'paciente';
  id: number;
  nombre: string;
  cedula: string;
}

export interface AdminSesion extends TokenSesion {
  tipo: 'admin';
  id: number;
  usuario: string;
  rol: string;
}

export type Sesion = PacienteSesion | AdminSesion;

@Injectable({ providedIn: 'root' })
export class SessionService {
  private sesion: Sesion | null = null;

  constructor() {
    // Retira el estado inseguro del taller anterior, sin tocar otras claves del navegador.
    localStorage.removeItem('vidaplena_sesion');
  }

  guardarSesion(sesion: Sesion): void {
    this.sesion = sesion;
  }

  obtenerSesion(): Sesion | null {
    if (this.sesion && Date.now() >= this.sesion.expira_en) this.cerrarSesion();
    return this.sesion;
  }

  esAdmin(): boolean {
    const sesion = this.obtenerSesion();
    return sesion?.tipo === 'admin' && sesion.rol === 'administrador';
  }

  cerrarSesion(): void {
    this.sesion = null;
  }
}
