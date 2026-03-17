
from logging import critical
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import time
from abc import ABC, abstractmethod
from enum import Enum
import warnings


class AdaptationMode(Enum):
    NONE = 0            # classic
    GAIN_SCHEDULING = 1 # operational point dependend
    MRAC = 2            # model reference
    SELF_TUNING = 3     # self optimized
    GRADIENT = 4        # gradient based


class BasePID(ABC):

    def __init__(self, setpoint=0, sample_time=0.01, output_limits=(None, None)):
        
        self.setpoint = setpoint
        self.sample_time = sample_time
        self.output_limits = output_limits
        
        # internal states
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.last_time = time.time()
        
        # history
        self.error_history = deque(maxlen=1000)
        self.output_history = deque(maxlen=1000)
        self.time_history = deque(maxlen=1000)
        
    @abstractmethod
    def calculate(self, feedback, current_time=None):
        pass
    
    def _apply_output_limits(self, output):
        if self.output_limits[0] is not None:
            output = max(self.output_limits[0], output)
        if self.output_limits[1] is not None:
            output = min(self.output_limits[1], output)
        return output
    
    def reset(self):
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.last_time = time.time()
        self.error_history.clear()
        self.output_history.clear()
        self.time_history.clear()
    
    def get_statistics(self):        
        if len(self.error_history) == 0:
            return {}        
        errors = np.array(self.error_history)
        return {
            'mse': np.mean(errors**2),
            'mae': np.mean(np.abs(errors)),
            'max': np.max(np.abs(errors)),
            'std': np.std(errors)
        }


class AdaptivePID(BasePID):
    
    def __init__(self, Kp=1.0, Ki=0.0, Kd=0.0, setpoint=0, 
                 sample_time=0.01, output_limits=(None, None)):
        
        super().__init__(setpoint, sample_time, output_limits)
        
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        
        self.base_Kp = Kp
        self.base_Ki = Ki
        self.base_Kd = Kd
                
        self.adaptation_mode = AdaptationMode.NONE
        self.adaptation_rate = 0.01         # learning rate
        self.adaptation_gain = 0.1          # gain for MRAC
        
        # anti-windup
        self.integral_limit = None          # integral limit
        self.anti_windup = True
        
        self.gain_schedule = []             # list of (operation point, (Kp, Ki, Kd)) tuples
        
        # MRAC
        self.reference_model = None         # reference function
        self.reference_output = 0
        
        # self optimization
        self.plant_model = None             # model proposed
        self.identification_interval = 50   # steps to identify
        self.step_count = 0
        
        # limits
        self.Kp_bounds = (0.01, 100.0)
        self.Ki_bounds = (0.0, 50.0)
        self.Kd_bounds = (0.0, 20.0)
        
        # derivative filter
        self.derivative_filter = 0.1        # low pass Kd
        self.filtered_derivative = 0
        
    def calculate(self, feedback, current_time=None):
        
        if current_time is None:
            current_time = time.time()
        
        dt = current_time - self.last_time
        
        if dt >= self.sample_time:
            
            error = self.setpoint - feedback

            self.error_history.append(error)
            self.time_history.append(current_time)
                        
            self._update_adaptive_parameters(error, feedback, dt)
                                    
            self.integral += error * dt
            if self.anti_windup and self.integral_limit:
                self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
                        
            derivative = (error - self.last_error) / dt
            self.filtered_derivative = (self.derivative_filter * derivative + 
                                       (1 - self.derivative_filter) * self.filtered_derivative)
                        
            output = (self.Kp * error + self.Ki * self.integral + self.Kd * self.filtered_derivative)
                        
            output = self._apply_output_limits(output)
                        
            self.last_error = error            
            self.last_output = output
            self.output_history.append(output)
            
            self.step_count += 1
            
            return output
    
        self.last_time = current_time
                
        return self.last_output
    
    def _update_adaptive_parameters(self, error, feedback, dt):
        
        if self.adaptation_mode == AdaptationMode.GAIN_SCHEDULING:
            self._apply_gain_scheduling(error, feedback)
            
        elif self.adaptation_mode == AdaptationMode.MRAC:
            self._apply_mrac(error, dt)
            
        elif self.adaptation_mode == AdaptationMode.SELF_TUNING:
            self._apply_self_tuning(error, dt)
            
        elif self.adaptation_mode == AdaptationMode.GRADIENT:
            self._apply_gradient_adaptation(error, dt)
    
    def _apply_gain_scheduling(self, error, feedback):
        
        if not self.gain_schedule:
            return
        
        operating_point = abs(error)
        
        for i, (op_point, gains) in enumerate(self.gain_schedule):

            if operating_point <= op_point:
            
                if i == 0:
                    self.Kp, self.Ki, self.Kd = gains
                else:
                    prev_op, prev_gains = self.gain_schedule[i-1]
                    fraction = (operating_point - prev_op) / (op_point - prev_op)
                    
                    self.Kp = prev_gains[0] + fraction * (gains[0] - prev_gains[0])
                    self.Ki = prev_gains[1] + fraction * (gains[1] - prev_gains[1])
                    self.Kd = prev_gains[2] + fraction * (gains[2] - prev_gains[2])

                    print(f"{self.Kp:.6f} {self.Ki:.6f} {self.Kd:.6f}")
                break
    
    def _apply_mrac(self, error, dt):
        """
        model reference adaptive control (MRAC)
        """
        if self.reference_model is None:
            return
        
        self.reference_output = self.reference_model(self.setpoint)
        
        model_error = self.reference_output - (self.setpoint - error)
        
        self.Kp += self.adaptation_gain * model_error * error * dt
        self.Ki += self.adaptation_gain * model_error * self.integral * dt
        self.Kd += self.adaptation_gain * model_error * self.filtered_derivative * dt
        
        self._clamp_parameters()
    
    def _apply_self_tuning(self, error, dt):
        
        if self.step_count % self.identification_interval != 0:
            return
        
        if len(self.error_history) < 20:
            return
        
        recent_errors = list(self.error_history)[-20:]
        error_std = np.std(recent_errors)
        error_mean = np.mean(np.abs(recent_errors))
        
        zero_crossings = sum(1 for i in range(1, len(recent_errors)) if recent_errors[i-1] * recent_errors[i] < 0)
        
        # heuristics
        if zero_crossings > 10 and error_std > 0.1 * abs(self.setpoint):
            # oszillation -> reduce Kp, increase Kd
            self.Kp *= 0.9
            self.Kd *= 1.1
            print(f"oscillation Kp={self.Kp:.3f}, Kd={self.Kd:.3f}")
            
        elif error_mean > 0.2 * abs(self.setpoint) and zero_crossings < 3:
            # huge error -> increase Kp, adapt Ki
            self.Kp *= 1.2
            self.Ki *= 1.05
            print(f"error Kp={self.Kp:.3f}, Ki={self.Ki:.3f}")
            
        elif error_mean < 0.05 * abs(self.setpoint) and self.integral > 0:
            # minimal error  -> optimize Ki
            if abs(error) > 0:
                self.Ki *= 0.95  # reduce minimal to avoid overshoot
        
        # clip
        self._clamp_parameters()
    
    def _apply_gradient_adaptation(self, error, dt):
        
        J = error**2
        
        # compute parameter gradients
        # (∂J/∂Kp)

        self.Kp -= self.adaptation_rate * error * error * dt
        self.Ki -= self.adaptation_rate * error * self.integral * dt
        self.Kd -= self.adaptation_rate * error * self.filtered_derivative * dt
        
        self._clamp_parameters()
    
    def _clamp_parameters(self):        
        self.Kp = np.clip(self.Kp, self.Kp_bounds[0], self.Kp_bounds[1])
        self.Ki = np.clip(self.Ki, self.Ki_bounds[0], self.Ki_bounds[1])
        self.Kd = np.clip(self.Kd, self.Kd_bounds[0], self.Kd_bounds[1])
    
    def configure_gain_scheduling(self, schedule):
        """                
        args:
            schedule: list by (operating point, (Kp, Ki, Kd)) tuples
            example: [(0, (1.0, 0.1, 0.05)), (10, (2.0, 0.3, 0.1))]
        """
        self.gain_schedule = sorted(schedule, key=lambda x: x[0])
        self.adaptation_mode = AdaptationMode.GAIN_SCHEDULING
    
    def configure_mrac(self, reference_model):
        self.reference_model = reference_model
        self.adaptation_mode = AdaptationMode.MRAC
    
    def configure_self_tuning(self):
        self.adaptation_mode = AdaptationMode.SELF_TUNING
    
    def set_parameter_bounds(self, Kp_min=0.01, Kp_max=100.0, 
                            Ki_min=0.0, Ki_max=50.0,
                            Kd_min=0.0, Kd_max=20.0):        
        self.Kp_bounds = (Kp_min, Kp_max)
        self.Ki_bounds = (Ki_min, Ki_max)
        self.Kd_bounds = (Kd_min, Kd_max)
    
    def get_current_parameters(self):
        return {
            'Kp': self.Kp,
            'Ki': self.Ki,
            'Kd': self.Kd,
            'mode': self.adaptation_mode.name
        }
    

class AutoTuner:
    
    def __init__(self, plant_func, sample_time=0.01):        
        self.plant = plant_func
        self.sample_time = sample_time
    
    def relay_feedback_test(self, setpoint, amplitude=10, cycles=3):
                
        state = 0
        outputs = []
        times = []
        zero_crossings = []

        idx = 0
        
        for i in range(int(cycles / self.sample_time)):
            
            t = i * self.sample_time
            
            if isinstance(state, (int, float)): 
                s = state
            else:
                s = state[idx]
            
            if s < setpoint - 0.5:
                control = amplitude
            elif s > setpoint + 0.5:
                control = -amplitude
            else:
                control = 0

            state = self.plant(state, control, self.sample_time)
            outputs.append(state)
            times.append(t)
            
            # crossings
            if len(outputs) > 1 and (outputs[-2][idx] - setpoint) * (outputs[-1][idx] - setpoint) < 0:
                zero_crossings.append(t)
        
        if len(zero_crossings) >= 4:

            # critical Tu
            periods = np.diff(zero_crossings[-4:])
            Tu = np.mean(periods[1:]) * 2            
            
            # critical Ku (Ziegler-Nichols)
            Ku = 4 * amplitude / (np.pi * np.mean(np.abs(outputs)))            

            print(f"{setpoint} {amplitude} {zero_crossings}")    
            print(f"{Ku:.3f}; {Tu:.3f}s")
            
            return Ku, Tu
        
        return None, None
    
    def ziegler_nichols(self, Ku, Tu, controller_type='pid'):        
        if controller_type == 'p':
            return (0.5 * Ku, 0, 0)
        elif controller_type == 'pi':
            return (0.45 * Ku, 0.54 * Ku / Tu, 0)
        else:  # pid
            return (0.6 * Ku, 1.2 * Ku / Tu, 0.075 * Ku * Tu)
    
    def auto_tune(self, setpoint, amplitude, cycles):
        Ku, Tu = self.relay_feedback_test(setpoint, amplitude, cycles)        
        if Ku is None or Tu is None:
            print(f"auto tune error {Ku} {Tu}")
            return (1.0, 0.1, 0.05)  # fallback        
        return self.ziegler_nichols(Ku, Tu)


class BidirectionalAdaptivePID(AdaptivePID):
    """
    Bidirektionaler adaptiver PID-Regler
    Getrennte Parameter für positive und negative Regelrichtung
    """
    
    def __init__(self, Kp_pos=1.0, Ki_pos=0.1, Kd_pos=0.05,
                 Kp_neg=1.0, Ki_neg=0.1, Kd_neg=0.05,
                 setpoint=0, sample_time=0.01, asymmetry_factor=1.0, output_limits=(None, None)):
        """
        Initialisiert den bidirektionalen PID mit getrennten Parametern
        """
        # Basis mit Standardparametern initialisieren
        super().__init__(Kp_pos, Ki_pos, Kd_pos, setpoint, sample_time, output_limits)
        
        # Separate Parameter für negative Richtung
        self.Kp_pos = Kp_pos
        self.Ki_pos = Ki_pos
        self.Kd_pos = Kd_pos
        
        self.Kp_neg = Kp_neg
        self.Ki_neg = Ki_neg
        self.Kd_neg = Kd_neg
        
        # Aktuelle Richtung
        self.current_direction = 0  # -1: negativ, 0: neutral, 1: positiv
        
        # Asymmetrie-Kompensation
        self.asymmetry_factor = asymmetry_factor
        self.deadzone = 0.0
    
    def _select_direction_params(self, error):
        """Wählt Parameter basierend auf Fehlerrichtung"""
        if error > self.deadzone:
            self.current_direction = 1
            self.Kp, self.Ki, self.Kd = self.Kp_pos, self.Ki_pos, self.Kd_pos
        elif error < -self.deadzone:
            self.current_direction = -1
            self.Kp, self.Ki, self.Kd = self.Kp_neg, self.Ki_neg, self.Kd_neg
        else:
            self.current_direction = 0
    
    def calculate(self, feedback, current_time=None):
        """
        Berechnet Stellgröße mit richtungsabhängigen Parametern
        """
        if current_time is None:
            current_time = time.time()
        
        dt = current_time - self.last_time
        
        if dt >= self.sample_time:
            error = self.setpoint - feedback
            
            # Richtungsspezifische Parameter auswählen
            self._select_direction_params(error)
            
            # Standard-PID-Berechnung mit aktuellen Parametern
            self.error_history.append(error)
            
            self.integral += error * dt
            if self.anti_windup and self.integral_limit:
                self.integral = np.clip(self.integral, 
                                       -self.integral_limit, 
                                       self.integral_limit)
            
            derivative = (error - self.last_error) / dt
            self.filtered_derivative = (self.derivative_filter * derivative + 
                                       (1 - self.derivative_filter) * self.filtered_derivative)
            
            output = (self.Kp * error + 
                     self.Ki * self.integral + 
                     self.Kd * self.filtered_derivative)
            
            # Asymmetrie-Kompensation
            if self.current_direction == -1:
                output *= self.asymmetry_factor
            
            output = self._apply_output_limits(output)
            
            self.last_error = error
            self.last_time = current_time
            self.last_output = output
            self.output_history.append(output)
            
            return output
        
        return self.last_output
    
    def adapt_asymmetry(self):
        """
        Passt den Asymmetrie-Faktor basierend auf Performance an
        """
        if len(self.error_history) < 100:
            return
        
        # Fehler nach Richtung trennen
        pos_errors = []
        neg_errors = []
        
        # Hier müsste man die Richtung für jeden Fehler speichern
        # Vereinfachte Version:
        recent_errors = list(self.error_history)[-100:]
        
        if self.asymmetry_factor < 1.0:
            self.asymmetry_factor *= 1.01
        else:
            self.asymmetry_factor *= 0.99
        
        self.asymmetry_factor = np.clip(self.asymmetry_factor, 0.1, 10.0)


def simulate_system(pid, plant_func, setpoint_profile, run_time=20, noise=0.0):
    """        
    args:
        pid                 instance
        plant_func          system function (state, control, dt) -> new_state
        setpoint_profile    list of (time, setpoint) tuples
        run_time            simulation run time
        noise               measurement noise default deviation
    
    returns:
        dict                simulation results
    """
    dt = pid.sample_time
    t = np.arange(0, run_time, dt)
    
    state = 0
    measurements = []
    setpoints = []
    controls = []
    
    Kp = []
    Ki = []
    Kd = []

    for time_point in t:

        current_setpoint = 0
        for set_time, set_value in setpoint_profile:
            if time_point >= set_time:
                current_setpoint = set_value
        
        pid.setpoint = current_setpoint
        setpoints.append(current_setpoint)
          
        if isinstance(state, (int, float)): 
            measurement = state + np.random.normal(0, noise)
        else:
            measurement = state[1] + np.random.normal(0, noise)
        measurements.append(measurement)
        
        control = pid.calculate(measurement, time_point)
        controls.append(control)
        
        params = pid.get_current_parameters()
        Kp.append(params['Kp'])
        Ki.append(params['Ki'])
        Kd.append(params['Kd'])
        
        # 
        state = plant_func(state, control, dt)
    
    return {
        't': t,
        'measurements': measurements,
        'setpoints': setpoints,
        'controls': controls,
        'history': [Kp, Ki, Kd],
        'pid': pid
    }

def plot_results(results, title=""):
   
    fig, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(5, 1, figsize=(21, 18))
    
    ax1.plot(results['t'], results['measurements'], 'b-', label='pv', linewidth=1)
    ax1.plot(results['t'], results['setpoints'], 'r--', label='sp', linewidth=1)
    ax1.set_ylabel('controlled')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title(title)
        
    ax2.plot(results['t'], results['controls'], 'g-', label='control', linewidth=1)
    ax2.set_ylabel('signal')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    ax3.plot(results['t'], results['history'][0], 'm-', label='Kp', linewidth=1)
    ax3.set_ylabel('Kp')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_xlabel('time (s)')

    ax4.plot(results['t'], results['history'][1], 'm-', label='Ki', linewidth=1)
    ax4.set_ylabel('Ki')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_xlabel('time (s)')

    ax5.plot(results['t'], results['history'][2], 'm-', label='Kd', linewidth=1)
    ax5.set_ylabel('Kd')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.set_xlabel('time (s)')        

    fig.set_label(title)
    plt.tight_layout()
    plt.show()

def example_pt2_system(state, control, dt):
    """
    Beispielsystem: PT2-Glied (schwingungsfähig)
    """
    omega = 2.0  # Eigenfrequenz
    D = 0.3      # Dämpfung
    
    if isinstance(state, (int, float)):
        x1, x2 = state, 0
    else:
        x1, x2 = state
    
    dx1 = x2
    dx2 = -2*D*omega*x2 - omega**2*x1 + omega**2*control
    
    x1_new = x1 + dx1 * dt
    x2_new = x2 + dx2 * dt
    
    return (x1_new, x2_new)

def example_nonlinear_system(state, control, dt):
    """
    Beispielsystem mit Nichtlinearität (ideal für bidirektionale Adaption)
    """
    # Asymmetrisches Verhalten: positive Richtung anders als negative
    if control > 0:
        # Positive Richtung: schnell, aber begrenzt
        return state + control * dt * 1.5
    else:
        # Negative Richtung: langsam mit Reibung
        friction = 0.1 * np.sign(control) * state**2
        return state + (control - friction) * dt

def _example():
    
    setpoint_profile = [
        ( 0,  0),
        ( 2, 10),   # jump to 10
        ( 6,  5),   # jump to  5
        (10, 15),   # jump to 15
        (14,  1),   # jump to  1
        (16,  3)    # jump to  3
    ]

    run_time = 20
    
    # classic
    
    pid_classic = AdaptivePID(Kp=1.0, Ki=0.1, Kd=0.05, sample_time=0.01)
    pid_classic.adaptation_mode = AdaptationMode.NONE
    
    results_classic = simulate_system(
        pid_classic, 
        example_pt2_system,
        setpoint_profile,
        run_time=run_time
    )        
    
    # gain scheduling

    pid_gs = AdaptivePID(Kp=1.0, Ki=0.2, Kd=0.05, sample_time=0.01)

    gs_schedule = [
        ( 0, (1.00, 0.10, 0.02)),   # small     moderate
        ( 3, (1.80, 0.20, 0.05)),   # middle    higher strength
        ( 7, (2.50, 0.30, 0.08)),   # high      aggressive
        (15, (1.20, 0.15, 0.03))    # very high moderate
    ]
    pid_gs.configure_gain_scheduling(gs_schedule)
    
    results_gs = simulate_system(
        pid_gs,
        example_pt2_system,
        setpoint_profile,
        run_time=run_time
    )
        
    # self optimized

    pid_so = AdaptivePID(Kp=1.2, Ki=0.2, Kd=0.08, sample_time=0.01)
    pid_so.configure_self_tuning()
    pid_so.set_parameter_bounds(Kp_min=0.5, Kp_max=3.0, Ki_max=0.5, Kd_max=0.2)
    
    results_so = simulate_system(
        pid_so,
        example_pt2_system,
        setpoint_profile,
        run_time=run_time
    )
        
    # 4. Bidirektionaler PID für asymmetrisches System
    #print("\n4. Bidirektionaler PID für asymmetrisches System")
    #pid_bi = BidirectionalAdaptivePID(
    #    Kp_pos=1.8, Ki_pos=0.25, Kd_pos=0.08,   # Aggressiver für positive Richtung
    #    Kp_neg=1.2, Ki_neg=0.15, Kd_neg=0.12,   # Konservativer für negative Richtung
    #    sample_time=0.01,
    #    asymmetry_factor=1.2
    #)
    
    #results_bi = simulate_system(
    #    pid_bi,
    #    example_nonlinear_system,
    #    setpoint_profile,
    #    run_time=run_time
    #)
    
    # auto tuning
    
    tuner = AutoTuner(example_pt2_system, sample_time=0.01)
    Kp_opt, Ki_opt, Kd_opt = tuner.auto_tune(setpoint=15, amplitude=20, cycles=10)
        
    pid_tuned = AdaptivePID(Kp_opt, Ki_opt, Kd_opt, sample_time=0.01)
        
    results_tuned = simulate_system(
        pid_tuned,
        example_pt2_system,
        setpoint_profile,
        run_time=run_time
    )
    
    #plot_results(results_classic, "classic")
    plot_results(results_gs, "gain scheduling")
    #plot_results(results_so, "self optimized")
    #plot_results(results_tuned, "auto tuned")

    #plot_results(results_bi, "bidirectional (asymmetric system)")
    
    def calculate_metrics(results):
        errors = np.array(results['setpoints']) - np.array(results['measurements'])
        return {
            'mse': np.mean(errors**2),
            'mae': np.mean(np.abs(errors)),
            'max': np.max(np.abs(errors)),
            'std': np.std(errors)
        }
    
    for name, results in [
        ("-----------classic", results_classic),
        ("---gain scheduling", results_gs),
        ("----self optimized", results_so),
        ("--------auto tuned", results_tuned)
    ]:
        metrics = calculate_metrics(results)
        print(f"\n{name}")
        print(f"    {results['pid'].base_Kp:.6f} {results['pid'].base_Ki:.6f} {results['pid'].base_Kd:.6f}")
        print(f"    {results['pid'].Kp:.6f} {results['pid'].Ki:.6f} {results['pid'].Kd:.6f}")
        print(f"mse {metrics['mse']:.4f}")
        print(f"mae {metrics['mae']:.4f}")
        print(f"max {metrics['max']:.4f}")
        print(f"std {metrics['std']:.4f}")


if __name__ == "__main__":

    import os
    os.system("cls")
    
    _example()
    
    # Einfaches Minimalbeispiel für den schnellen Einstieg
    #print("\n" + "=" * 60)
    #print("MINIMALBEISPIEL")
    #print("=" * 60)
    
    # PID mit Selbstoptimierung erstellen
    #pid = AdaptivePID(Kp=1.0, Ki=0.2, Kd=0.05, setpoint=10)
    #pid.configure_self_tuning()
    
    # Einfache Simulation
    #state = 1.0
    #for i in range(200):

    #    output = pid.calculate(state)
    #    state = example_pt2_system(state, output, pid.sample_time)
        
    #    if i % 50 == 0:
    #        params = pid.get_current_parameters()
    #        print(f"Schritt {i}: state={state}, Kp={params['Kp']:.3f}")
    
    #print(f"\nEndzustand: {state}")
    #print(f"Statistik: {pid.get_statistics()}")