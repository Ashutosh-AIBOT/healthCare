import { StatCard } from "@/components/dashboard/stat-card";
import { ServiceCard } from "@/components/dashboard/service-card";
import { ProviderCard } from "@/components/dashboard/provider-card";
import { ActivityChart } from "@/components/dashboard/activity-chart";

export default function AppHomePage() {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Dashboard</h1>
        <p className="text-sm text-muted">Your health, effortlessly managed.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Patients" value="1,245" trend="+4.2% this week" color="primary" />
        <StatCard label="Doctors" value="86" trend="+2 new" color="primary" />
        <StatCard label="Appointments" value="342" trend="+12% this week" color="primary" />
        <StatCard label="Reports" value="128" trend="Pending 5" color="primary" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold tracking-tight text-ink">Your Health, Effortlessly Managed.</h2>
              <p className="max-w-xl text-sm text-muted">
                Connect with trusted providers, track appointments, and access lab reports all in one place.
              </p>
            </div>
            <div className="h-40 w-40 shrink-0 rounded-[1.25rem] bg-mist md:h-48 md:w-48" aria-hidden />
          </div>
        </div>
        <ActivityChart />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Popular Services</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <ServiceCard title="Doctors" description="Consult specialists" icon="doctors" color="primary" />
            <ServiceCard title="Lab Tests" description="Diagnostics at home" icon="labs" color="primary" />
            <ServiceCard title="Pharmacy" description="Medicines delivered" icon="pharmacy" color="primary" />
            <ServiceCard title="Emergency" description="24/7 ambulance" icon="ambulance" color="primary" />
          </div>
        </div>
        <div className="space-y-3">
          <h2 className="font-semibold text-ink">Best Providers</h2>
          <div className="space-y-3">
            <ProviderCard name="Dr. Anika Patel" specialty="Cardiology" available />
            <ProviderCard name="Dr. Riya Sharma" specialty="Dermatology" />
            <ProviderCard name="Dr. Kavya Nair" specialty="Pediatrics" available />
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Total Checkups</p>
          <p className="mt-2 text-2xl font-semibold text-ink">45K+</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Happy Patients</p>
          <p className="mt-2 text-2xl font-semibold text-ink">20K+</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Expert Doctors</p>
          <p className="mt-2 text-2xl font-semibold text-ink">150+</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Awards</p>
          <p className="mt-2 text-2xl font-semibold text-ink">30+</p>
        </div>
      </div>
    </div>
  );
}
