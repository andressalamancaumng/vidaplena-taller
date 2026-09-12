import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { SessionService } from './session.service';

/** Mejora la navegación; la autorización efectiva siempre se valida también en FastAPI. */
export const adminGuard: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);

  if (session.esAdmin()) {
    return true;
  }

  router.navigate(['/login']);
  return false;
};
