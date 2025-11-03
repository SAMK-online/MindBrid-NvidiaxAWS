import { useEffect, useState } from 'react';

const API_URL = 'http://localhost:8000';

const SPECIALIZATION_OPTIONS = [
  'anxiety',
  'depression',
  'trauma',
  'addiction',
  'relationships',
  'grief',
  'eating_disorders',
  'ocd',
  'ptsd',
  'general'
] as const;

type TimeSlot = {
  day_of_week: string;
  start_time: string;
  end_time: string;
  timezone?: string;
  is_available?: boolean;
  recurring?: boolean;
};

type Therapist = {
  id?: string;
  name?: string;
  email?: string;
  phone?: string;
  specializations?: string[];
  license_number?: string;
  years_experience?: number;
  time_slots?: TimeSlot[];
  is_volunteer?: boolean;
  status?: string;
  max_patients?: number;
  current_patients?: number;
  bio?: string;
};

export default function TherapistsPage() {
  const [activeTab, setActiveTab] = useState<'add' | 'list'>('add');
  return (
    <div className="app">
      <div className="container wide">
        <h1>🧑‍⚕️ Therapists</h1>
        <p className="subtitle">Register new therapists and view active ones</p>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'add' ? 'active' : ''}`}
            onClick={() => setActiveTab('add')}
          >
            Add Therapist
          </button>
          <button
            className={`tab ${activeTab === 'list' ? 'active' : ''}`}
            onClick={() => setActiveTab('list')}
          >
            All Therapists
          </button>
        </div>

        {activeTab === 'add' ? <TherapistForm /> : <TherapistList />}
      </div>
    </div>
  );
}

function TherapistForm() {
  const [form, setForm] = useState<Therapist>({
    is_volunteer: true,
    status: 'active',
    specializations: [],
    time_slots: [
      { day_of_week: 'Monday', start_time: '09:00', end_time: '17:00', timezone: 'America/New_York', is_available: true, recurring: true },
    ],
    years_experience: 0,
    max_patients: 10,
    current_patients: 0,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [licenseImage, setLicenseImage] = useState<File | null>(null);
  const [licenseImagePreview, setLicenseImagePreview] = useState<string | null>(null);

  const handleChange = (key: keyof Therapist, value: any) => {
    setForm(prev => ({ ...prev, [key]: value }));
  };

  const updateSlot = (idx: number, key: keyof TimeSlot, value: any) => {
    setForm(prev => {
      const slots = [...(prev.time_slots || [])];
      slots[idx] = { ...(slots[idx] || {}), [key]: value } as TimeSlot;
      return { ...prev, time_slots: slots };
    });
  };

  const addSlot = () => {
    setForm(prev => ({
      ...prev,
      time_slots: [
        ...(prev.time_slots || []),
        { day_of_week: 'Tuesday', start_time: '09:00', end_time: '17:00', timezone: 'America/New_York', is_available: true, recurring: true },
      ],
    }));
  };

  const removeSlot = (idx: number) => {
    setForm(prev => ({
      ...prev,
      time_slots: (prev.time_slots || []).filter((_, i) => i !== idx),
    }));
  };

  const addSpec = (spec: string) => {
    if (!spec) return;
    setForm(prev => ({ ...prev, specializations: Array.from(new Set([...(prev.specializations || []), spec])) }));
  };

  const removeSpec = (v: string) => {
    setForm(prev => ({ ...prev, specializations: (prev.specializations || []).filter(s => s !== v) }));
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
      if (!validTypes.includes(file.type) && !file.type.startsWith('image/')) {
        setMessage('Please upload a valid image file (JPEG, PNG, or PDF)');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setMessage('File size must be less than 5MB');
        return;
      }

      setLicenseImage(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setLicenseImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
      setMessage(null);
    }
  };

  const removeLicenseImage = () => {
    setLicenseImage(null);
    setLicenseImagePreview(null);
  };

  const validateForm = (): string | null => {
    if (!form.name || !form.name.trim()) return 'Name is required';
    if (!form.email || !form.email.trim()) return 'Email is required';
    if (!form.phone || !form.phone.trim()) return 'Phone is required';
    if (!form.license_number || !form.license_number.trim()) return 'License number is required';
    if (!Array.isArray(form.specializations) || form.specializations.length === 0) return 'Select at least one specialization';
    if (licenseImage == null) return 'Licence file is required';
    if (form.years_experience === undefined || form.years_experience === null || Number.isNaN(form.years_experience)) return 'Years of experience is required';
    if (form.max_patients === undefined || form.max_patients === null) return 'Max patients is required';
    if (form.current_patients === undefined || form.current_patients === null) return 'Current patients is required';
    if (!form.time_slots || form.time_slots.length === 0) return 'At least one time slot is required';
    const invalidSlot = (form.time_slots || []).find(s => !s.day_of_week || !s.start_time || !s.end_time || !s.timezone);
    if (invalidSlot) return 'Each time slot must include day, start, end, and timezone';
    return null;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    const validationError = validateForm();
    if (validationError) {
      setMessage(validationError);
      return;
    }
    setSaving(true);
    try {
      const payload: Therapist = { ...form };
      // First: register therapist
      const res = await fetch(`${API_URL}/therapist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Failed to register');

      const therapistId: string | undefined = data?.therapist?.id;
      if (!therapistId) {
        throw new Error('Registered but missing therapist_id in response');
      }

      // Second: upload licence if provided
      if (licenseImage) {
        const fd = new FormData();
        fd.append('file', licenseImage);
        const upRes = await fetch(`${API_URL}/therapist/licence-upload?therapist-id=${encodeURIComponent(therapistId)}`,
          { method: 'POST', body: fd }
        );
        const upData = await upRes.json().catch(() => ({}));
        if (!upRes.ok) {
          throw new Error(upData?.detail || 'Therapist created, but licence upload failed');
        }
      }

      setMessage('Therapist registered and licence uploaded successfully');
      // Reset form on success
      setForm({
        is_volunteer: true,
        status: 'active',
        specializations: [],
        time_slots: [
          { day_of_week: 'Monday', start_time: '09:00', end_time: '17:00', timezone: 'America/New_York', is_available: true, recurring: true },
        ],
        years_experience: 0,
        max_patients: 10,
        current_patients: 0,
      });
      setLicenseImage(null);
      setLicenseImagePreview(null);
    } catch (err: any) {
      setMessage(err?.message || 'Error registering therapist');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="panel" onSubmit={onSubmit}>
      {message && <div className="notice">{message}</div>}
      <div className="grid">
        <div>
          <label>Name</label>
          <input required value={form.name || ''} onChange={e => handleChange('name', e.target.value)} placeholder="Dr. Alex Rivera" />
        </div>
        <div>
          <label>Email</label>
          <input required type="email" value={form.email || ''} onChange={e => handleChange('email', e.target.value)} placeholder="alex@mindbridge.org" />
        </div>
        <div>
          <label>Phone</label>
          <input required value={form.phone || ''} onChange={e => handleChange('phone', e.target.value)} placeholder="+1-555-0111" />
        </div>
        <div className="full">
          <label>Specializations</label>
          <div className="chips">
            {(form.specializations || []).map(s => (
              <span key={s} className="chip" onClick={() => removeSpec(s)}>{s} ✕</span>
            ))}
          </div>
          <div className="spec-grid">
            {SPECIALIZATION_OPTIONS.map(spec => (
              <button
                key={spec}
                type="button"
                className={`spec-option ${(form.specializations || []).includes(spec) ? 'selected' : ''}`}
                onClick={() => {
                  if ((form.specializations || []).includes(spec)) {
                    removeSpec(spec);
                  } else {
                    addSpec(spec);
                  }
                }}
              >
                {spec.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
        <div className="full">
          <label>License Number</label>
          <input required value={form.license_number || ''} onChange={e => handleChange('license_number', e.target.value)} placeholder="LMHC-45678-NY" />
        </div>
        <div className="full">
          <label>License Image</label>
          <div className="license-upload">
            {!licenseImagePreview ? (
              <label className="upload-area">
                <input 
                  type="file" 
                  accept="image/*,.pdf" 
                  onChange={handleImageChange}
                  style={{ display: 'none' }}
                />
                <div className="upload-placeholder">
                  <span className="upload-icon">📄</span>
                  <span className="upload-text">Click to upload license</span>
                  <span className="upload-hint">JPEG, PNG, or PDF (max 5MB)</span>
                </div>
              </label>
            ) : (
              <div className="license-preview">
                <img src={licenseImagePreview} alt="License preview" className="preview-image" />
                <button 
                  type="button" 
                  className="remove-image" 
                  onClick={removeLicenseImage}
                  aria-label="Remove license image"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </div>
        <div>
          <label>Years Experience</label>
          <input required type="number" value={form.years_experience ?? 0} onChange={e => handleChange('years_experience', Number(e.target.value))} />
        </div>
        <div>
          <label>Max Patients</label>
          <input required type="number" value={form.max_patients ?? 10} onChange={e => handleChange('max_patients', Number(e.target.value))} />
        </div>
        <div>
          <label>Current Patients</label>
          <input required type="number" value={form.current_patients ?? 0} onChange={e => handleChange('current_patients', Number(e.target.value))} />
        </div>
        <div>
          <label>Status</label>
          <div className="segmented">
            {['Active','InActive'].map(s => (
              <button
                type="button"
                key={s}
                className={`seg-btn ${((form.status||'active')===s)?'active':''}`}
                onClick={() => handleChange('status', s)}
              >{s}</button>
            ))}
          </div>
        </div>
        <div>
          <label>Volunteer</label>
          <div className="segmented">
            {[
              {label:'Yes', value:true},
              {label:'No', value:false},
            ].map(opt => (
              <button
                type="button"
                key={String(opt.value)}
                className={`seg-btn ${(form.is_volunteer??true)===opt.value?'active':''}`}
                onClick={() => handleChange('is_volunteer', opt.value)}
              >{opt.label}</button>
            ))}
          </div>
        </div>
        <div className="full">
          <label>Bio</label>
          <textarea value={form.bio || ''} onChange={e => handleChange('bio', e.target.value)} rows={3} />
        </div>
      </div>

        <div className="slots">
          <div className="slots-header">
            <h3>Time Slots</h3>
            <button type="button" className="chip-button" onClick={addSlot}>＋ Add Slot</button>
          </div>
        {(form.time_slots || []).map((slot, idx) => (
          <div key={idx} className="slot-row">
            <input value={slot.day_of_week} onChange={e => updateSlot(idx, 'day_of_week', e.target.value)} placeholder="Monday" />
            <input value={slot.start_time} onChange={e => updateSlot(idx, 'start_time', e.target.value)} placeholder="09:00" />
            <input value={slot.end_time} onChange={e => updateSlot(idx, 'end_time', e.target.value)} placeholder="17:00" />
            <input value={slot.timezone || ''} onChange={e => updateSlot(idx, 'timezone', e.target.value)} placeholder="America/New_York" />
            <button type="button" className="small" onClick={() => removeSlot(idx)}>Remove</button>
          </div>
        ))}
      </div>

      <div className="actions">
        <button type="submit" disabled={saving} className="primary">
          {saving ? 'Saving…' : 'Submit'}
        </button>
      </div>
    </form>
  );
}

function TherapistList() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/therapists`);
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Failed to fetch');
      setItems(data.therapists || []);
    } catch (err: any) {
      setError(err?.message || 'Error loading therapists');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <div className="panel">Loading…</div>;
  if (error) return <div className="panel notice">{error}</div>;

  return (
    <div className="panel list">
      {items.length === 0 && <div>No therapists found.</div>}
      {items.map((t: any) => (
        <div key={t.id} className="therapist-card">
          <div className="card-header">
            <div className={`status-dot ${t.status === 'active' ? 'on' : 'off'}`} />
            <div className="name">{t.name || t.id}</div>
          </div>
          <div className="card-body">
            <div className="row">
              <span className="label">Email</span>
              <span>{t.email}</span>
            </div>
            <div className="row">
              <span className="label">Specializations</span>
              <span>{(t.specializations || []).join(', ')}</span>
            </div>
            <div className="row">
              <span className="label">Capacity</span>
              <span>{t.current_patients}/{t.max_patients}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
