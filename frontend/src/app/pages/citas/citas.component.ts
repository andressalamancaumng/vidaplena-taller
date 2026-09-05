import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { InputTextarea } from 'primeng/inputtextarea';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { MessageModule } from 'primeng/message';
import { DividerModule } from 'primeng/divider';

import { ApiService } from '../../core/api.service';
import { SessionService } from '../../core/session.service';

@Component({
  selector: 'app-citas',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    CardModule,
    InputTextModule,
    InputTextarea,
    ButtonModule,
    TableModule,
    MessageModule,
    DividerModule,
  ],
  template: `
    <div class="vp-contenido">
      <p-card *ngIf="!sesionPaciente" header="Mis citas">
        <p>Debes iniciar sesión como paciente para agendar o ver tus citas.</p>
      </p-card>

      <ng-container *ngIf="sesionPaciente as sp">
        <p-card header="Agendar nueva cita" class="vp-card-separada">
          <form [formGroup]="formulario" (ngSubmit)="agendar()">
            <div class="vp-form-fila">
              <div class="vp-form-campo">
                <label for="fecha">Fecha</label>
                <input pInputText type="date" id="fecha" formControlName="fecha" />
              </div>
              <div class="vp-form-campo">
                <label for="hora">Hora</label>
                <input pInputText type="time" id="hora" formControlName="hora" />
              </div>
              <div class="vp-form-campo">
                <label for="medico">Médico</label>
                <input pInputText id="medico" formControlName="medico" placeholder="Dra. Valentina Ríos" />
              </div>
            </div>
            <div class="vp-form-campo">
              <label for="motivo">Motivo de consulta</label>
              <input pInputText id="motivo" formControlName="motivo_consulta" />
            </div>
            <div class="vp-form-campo">
              <label for="diagnostico">Diagnóstico (si ya fue atendido/a)</label>
              <textarea pInputTextarea id="diagnostico" formControlName="diagnostico" rows="2"></textarea>
            </div>

            <p-message *ngIf="mensaje" [severity]="mensajeTipo" [text]="mensaje"></p-message>

            <button
              pButton
              type="submit"
              label="Guardar cita"
              icon="pi pi-calendar-plus"
              [disabled]="formulario.invalid"
              style="margin-top:0.5rem;"
            ></button>
          </form>
        </p-card>

        <p-card header="Mis citas ({{ sp.nombre }})" class="vp-card-separada">
          <p-table [value]="misCitas" [tableStyle]="{ 'min-width': '30rem' }">
            <ng-template pTemplate="header">
              <tr>
                <th>ID</th>
                <th>Fecha</th>
                <th>Hora</th>
                <th>Médico</th>
                <th>Motivo</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-fila>
              <tr>
                <td>{{ fila.id }}</td>
                <td>{{ fila.fecha }}</td>
                <td>{{ fila.hora }}</td>
                <td>{{ fila.medico }}</td>
                <td>{{ fila.motivo_consulta }}</td>
              </tr>
            </ng-template>
          </p-table>
        </p-card>
      </ng-container>

      <p-divider></p-divider>

      <p-card header="Consultar el detalle de una cita por número">
        <p class="vp-ayuda">
          Útil si un paciente pregunta por el detalle exacto de una cita puntual (por ejemplo,
          para confirmar el diagnóstico registrado).
        </p>
        <div class="vp-form-fila">
          <div class="vp-form-campo">
            <label for="citaId">Número de cita</label>
            <input pInputText id="citaId" type="number" [(ngModel)]="citaIdConsulta" [ngModelOptions]="{standalone: true}" />
          </div>
          <div class="vp-form-campo" style="justify-content:flex-end;">
            <button pButton label="Consultar" icon="pi pi-eye" (click)="consultarCita()"></button>
          </div>
        </div>

        <p-message *ngIf="errorConsulta" severity="error" [text]="errorConsulta"></p-message>

        <div *ngIf="citaConsultada" style="margin-top:1rem;">
          <p><strong>Paciente:</strong> {{ citaConsultada.nombre }}</p>
          <p><strong>Fecha:</strong> {{ citaConsultada.fecha }} — {{ citaConsultada.hora }}</p>
          <p><strong>Médico:</strong> {{ citaConsultada.medico }}</p>
          <p><strong>Motivo de consulta:</strong> {{ citaConsultada.motivo_consulta }}</p>
          <p><strong>Diagnóstico:</strong> {{ citaConsultada.diagnostico }}</p>
        </div>
      </p-card>
    </div>
  `,
})
export class CitasComponent implements OnInit {
  sesionPaciente: { id: number; nombre: string; cedula: string } | null = null;
  misCitas: any[] = [];

  private fb = inject(FormBuilder);

  formulario = this.fb.group({
    fecha: ['', Validators.required],
    hora: ['', Validators.required],
    medico: ['', Validators.required],
    motivo_consulta: [''],
    diagnostico: [''],
  });

  mensaje = '';
  mensajeTipo: 'success' | 'error' = 'success';

  citaIdConsulta: number | null = null;
  citaConsultada: any = null;
  errorConsulta = '';

  constructor(
    private api: ApiService,
    private session: SessionService,
  ) {}

  ngOnInit(): void {
    const sesion = this.session.obtenerSesion();
    if (sesion?.tipo === 'paciente') {
      this.sesionPaciente = sesion;
      this.cargarMisCitas();
    }
  }

  cargarMisCitas(): void {
    if (!this.sesionPaciente) return;
    this.api.citasDePaciente(this.sesionPaciente.id).subscribe((datos) => (this.misCitas = datos));
  }

  agendar(): void {
    if (this.formulario.invalid || !this.sesionPaciente) return;

    const valores = this.formulario.value;
    this.api
      .crearCita({
        paciente_id: this.sesionPaciente.id,
        fecha: valores.fecha as string,
        hora: `${valores.hora}:00`,
        medico: valores.medico as string,
        motivo_consulta: valores.motivo_consulta || undefined,
        diagnostico: valores.diagnostico || undefined,
      })
      .subscribe({
        next: () => {
          this.mensaje = 'Cita agendada correctamente.';
          this.mensajeTipo = 'success';
          this.formulario.reset();
          this.cargarMisCitas();
        },
        error: (err) => {
          this.mensaje = err?.error?.detail ?? 'No se pudo agendar la cita.';
          this.mensajeTipo = 'error';
        },
      });
  }

  consultarCita(): void {
    if (!this.citaIdConsulta) return;
    this.errorConsulta = '';
    this.citaConsultada = null;
    this.api.obtenerCitaPorId(this.citaIdConsulta).subscribe({
      next: (datos) => (this.citaConsultada = datos),
      error: (err) => (this.errorConsulta = err?.error?.detail ?? 'No se pudo consultar la cita.'),
    });
  }
}
