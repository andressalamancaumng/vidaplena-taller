import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { SessionService } from './session.service';

/**
 * Adjunta automáticamente el header `Authorization: Bearer <token>` a toda
 * solicitud saliente, cuando hay una sesión guardada. Es la contraparte en
 * el cliente de la Falla 2/3 corregidas en el backend: sin este header, el
 * backend rechaza (401/403) los endpoints que ahora exigen sesión.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const session = inject(SessionService);
  const token = session.obtenerToken();

  if (!token) {
    return next(req);
  }

  const reqConToken = req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
  return next(reqConToken);
};
