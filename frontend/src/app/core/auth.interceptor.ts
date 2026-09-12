import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { API_URL } from './api.config';
import { SessionService } from './session.service';

/** Adjunta la credencial una sola vez y únicamente a peticiones de nuestra API. */
export const authInterceptor: HttpInterceptorFn = (peticion, siguiente) => {
  const session = inject(SessionService);
  const router = inject(Router);
  const sesion = session.obtenerSesion();
  const esApi = peticion.url.startsWith(`${API_URL}/`);
  const autenticada = esApi && sesion
    ? peticion.clone({ setHeaders: { Authorization: `Bearer ${sesion.access_token}` } })
    : peticion;

  return siguiente(autenticada).pipe(catchError((error: HttpErrorResponse) => {
    if (esApi && error.status === 401 && sesion) {
      session.cerrarSesion();
      router.navigate(['/login']);
    }
    return throwError(() => error);
  }));
};
