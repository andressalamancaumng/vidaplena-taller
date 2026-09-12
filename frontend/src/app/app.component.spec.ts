import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { AppComponent } from './app.component';
import { ApiService } from './core/api.service';
import { SessionService } from './core/session.service';

describe('AppComponent', () => {
  const api = jasmine.createSpyObj('ApiService', ['cerrarSesion']);

  beforeEach(async () => {
    api.cerrarSesion.and.returnValue(of({}));
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideRouter([]), provideNoopAnimations(), { provide: ApiService, useValue: api }],
    }).compileComponents();
  });

  it('muestra VidaPlena', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('VidaPlena');
  });

  it('revoca la sesión antes de borrar el estado local', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const sesion = TestBed.inject(SessionService);
    sesion.guardarSesion({
      tipo: 'admin', id: 1, usuario: 'admin', rol: 'administrador',
      access_token: 'token_de_prueba', expira_en: Date.now() + 60000,
    });
    spyOn(TestBed.inject(Router), 'navigate').and.returnValue(Promise.resolve(true));
    fixture.componentInstance.cerrarSesion();
    expect(api.cerrarSesion).toHaveBeenCalled();
    expect(sesion.obtenerSesion()).toBeNull();
  });
});
