import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';

import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-registro',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    CardModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    MessageModule,
  ],
  template: `
    <div class="vp-contenido">
      <p-card header="Registro de paciente">
        <form [formGroup]="formulario" (ngSubmit)="registrar()">
          <div class="vp-form-fila">
            <div class="vp-form-campo">
              <label for="nombre">Nombre completo</label>
              <input pInputText id="nombre" formControlName="nombre" />
            </div>
            <div class="vp-form-campo">
              <label for="cedula">Cédula</label>
              <input pInputText id="cedula" formControlName="cedula" />
            </div>
          </div>
          <div class="vp-form-fila">
            <div class="vp-form-campo">
              <label for="telefono">Teléfono</label>
              <input pInputText id="telefono" formControlName="telefono" />
            </div>
            <div class="vp-form-campo">
              <label for="correo">Correo</label>
              <input pInputText id="correo" formControlName="correo" />
            </div>
          </div>
          <div class="vp-form-campo">
            <label for="contrasena">Contraseña (mínimo 12 caracteres; máximo 72 bytes)</label>
            <p-password
              id="contrasena"
              formControlName="contrasena"
              [feedback]="false"
              [toggleMask]="true"
            ></p-password>
          </div>

          <p-message *ngIf="mensaje" [severity]="mensajeTipo" [text]="mensaje"></p-message>

          <button
            pButton
            type="submit"
            label="Registrarme"
            icon="pi pi-check"
            [disabled]="formulario.invalid || enviando"
            style="margin-top: 1rem;"
          ></button>
        </form>
      </p-card>
    </div>
  `,
})
export class RegistroComponent {
  private fb = inject(FormBuilder);

  formulario = this.fb.group({
    nombre: ['', Validators.required],
    cedula: ['', Validators.required],
    telefono: [''],
    correo: [''],
    contrasena: ['', [Validators.required, Validators.minLength(12), Validators.maxLength(72)]],
  });

  mensaje = '';
  mensajeTipo: 'success' | 'error' = 'success';
  enviando = false;

  constructor(
    private api: ApiService,
    private router: Router,
  ) {}

  registrar(): void {
    if (this.formulario.invalid) {
      return;
    }
    this.enviando = true;
    this.api.registrarPaciente(this.formulario.value as any).subscribe({
      next: () => {
        this.mensaje = 'Registro exitoso. Ya puedes iniciar sesión.';
        this.mensajeTipo = 'success';
        this.enviando = false;
        setTimeout(() => this.router.navigate(['/login']), 1200);
      },
      error: (err) => {
        this.mensaje = err?.error?.detail ?? 'No se pudo completar el registro.';
        this.mensajeTipo = 'error';
        this.enviando = false;
      },
    });
  }
}
