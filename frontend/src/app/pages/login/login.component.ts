import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { SelectButtonModule } from 'primeng/selectbutton';
import { MessageModule } from 'primeng/message';

import { ApiService } from '../../core/api.service';
import { SessionService } from '../../core/session.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    CardModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    SelectButtonModule,
    MessageModule,
  ],
  template: `
    <div class="vp-contenido">
      <p-card header="Iniciar sesión">
        <div class="vp-form-campo">
          <label>Tipo de usuario</label>
          <p-selectButton
            [options]="tiposUsuario"
            [(ngModel)]="tipoSeleccionado"
            optionLabel="label"
            optionValue="value"
          ></p-selectButton>
        </div>

        <form [formGroup]="formulario" (ngSubmit)="ingresar()">
          <div class="vp-form-campo">
            <label for="identificador">
              {{ tipoSeleccionado === 'paciente' ? 'Cédula' : 'Usuario' }}
            </label>
            <input pInputText id="identificador" formControlName="identificador" />
          </div>
          <div class="vp-form-campo">
            <label for="contrasena">Contraseña</label>
            <p-password
              id="contrasena"
              formControlName="contrasena"
              [feedback]="false"
              [toggleMask]="true"
            ></p-password>
          </div>

          <p-message *ngIf="mensaje" severity="error" [text]="mensaje"></p-message>

          <button
            pButton
            type="submit"
            label="Ingresar"
            icon="pi pi-sign-in"
            [disabled]="formulario.invalid || enviando"
            style="margin-top: 1rem;"
          ></button>
        </form>

        <p class="vp-ayuda" style="margin-top:1rem;">
          Usuarios de ejemplo — paciente: cédula <code>1010023456</code>, contraseña
          <code>Cl4veSegura123</code>. Administrador: usuario <code>admin</code>, contraseña
          <code>Admin123!</code>.
        </p>
      </p-card>
    </div>
  `,
})
export class LoginComponent {
  tiposUsuario = [
    { label: 'Paciente', value: 'paciente' },
    { label: 'Administrador', value: 'admin' },
  ];
  tipoSeleccionado: 'paciente' | 'admin' = 'paciente';

  private fb = inject(FormBuilder);

  formulario = this.fb.group({
    identificador: ['', Validators.required],
    contrasena: ['', Validators.required],
  });

  mensaje = '';
  enviando = false;

  constructor(
    private api: ApiService,
    private session: SessionService,
    private router: Router,
  ) {}

  ingresar(): void {
    if (this.formulario.invalid) {
      return;
    }
    this.enviando = true;
    this.mensaje = '';

    const datos = this.formulario.value as any;
    const peticion =
      this.tipoSeleccionado === 'paciente'
        ? this.api.loginPaciente(datos)
        : this.api.loginAdmin(datos);

    peticion.subscribe({
      next: (respuesta) => {
        this.enviando = false;
        if (this.tipoSeleccionado === 'paciente') {
          this.session.guardarSesion({
            tipo: 'paciente',
            id: respuesta.id,
            nombre: respuesta.nombre,
            cedula: respuesta.cedula,
            contrasena: datos.contrasena,
          });
          this.router.navigate(['/citas']);
        } else {
          this.session.guardarSesion({
            tipo: 'admin',
            id: respuesta.id,
            usuario: respuesta.usuario,
            rol: respuesta.rol,
          });
          this.router.navigate(['/admin']);
        }
      },
      error: (err) => {
        this.mensaje = err?.error?.detail ?? 'No se pudo iniciar sesión.';
        this.enviando = false;
      },
    });
  }
}
