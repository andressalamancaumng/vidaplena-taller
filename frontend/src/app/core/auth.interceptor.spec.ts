import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';

import { authInterceptor } from './auth.interceptor';
import { SessionService } from './session.service';

describe('Credenciales de la API', () => {
  let http: HttpClient;
  let peticiones: HttpTestingController;
  let sesion: SessionService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideRouter([]), provideHttpClient(withInterceptors([authInterceptor])), provideHttpClientTesting(),
    ] });
    http = TestBed.inject(HttpClient);
    peticiones = TestBed.inject(HttpTestingController);
    sesion = TestBed.inject(SessionService);
    sesion.guardarSesion({
      tipo: 'paciente', id: 1, nombre: 'Prueba', cedula: '1111111111',
      access_token: 'token_de_prueba', expira_en: Date.now() + 60000,
    });
  });

  afterEach(() => peticiones.verify());

  it('envía el Bearer solo a nuestra API', () => {
    http.get('/api/citas/1').subscribe();
    const propia = peticiones.expectOne('/api/citas/1');
    expect(propia.request.headers.get('Authorization')).toBe('Bearer token_de_prueba');
    propia.flush({});
    http.get('https://example.com/api/').subscribe();
    const externa = peticiones.expectOne('https://example.com/api/');
    expect(externa.request.headers.has('Authorization')).toBeFalse();
    externa.flush({});
  });

  it('limpia la sesión cuando el servidor rechaza el token', () => {
    const navegar = spyOn(TestBed.inject(Router), 'navigate').and.returnValue(Promise.resolve(true));
    http.get('/api/citas/1').subscribe({ error: () => {} });
    peticiones.expectOne('/api/citas/1').flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(sesion.obtenerSesion()).toBeNull();
    expect(navegar).toHaveBeenCalledWith(['/login']);
  });

  it('descarta una sesión vencida', () => {
    const actual = sesion.obtenerSesion()!;
    sesion.guardarSesion({ ...actual, expira_en: Date.now() - 1 });
    expect(sesion.obtenerSesion()).toBeNull();
  });
});
