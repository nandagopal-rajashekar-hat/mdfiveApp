import React, { useRef, useState } from 'react';
import { Alert, Button, Card, Col, Container, Form, Row, Table } from 'react-bootstrap';
import * as XLSX from 'xlsx';
import SideBar from '../SideBar';

interface ExcelSignupRow { FirstName?: string; LastName?: string; Email?: string; Mobile?: string; Password?: string; ConfirmPassword?: string }

const SignUp: React.FC = () => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [headless, setHeadless] = useState(true);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger' | 'warning'; message: string } | null>(null);
  const [showResult, setShowResult] = useState<{ title: string; output?: string; error?: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<Array<ExcelSignupRow & { id: string }>>([]);

  const runSignup = async (row?: ExcelSignupRow) => {
    const payload = row ? {
      first_name: row.FirstName || '',
      last_name: row.LastName || '',
      email: row.Email || '',
      mobile: row.Mobile || '',
      password: row.Password || '',
      confirm_password: row.ConfirmPassword || row.Password || '',
    } : {
      first_name: firstName,
      last_name: lastName,
      email,
      mobile,
      password,
      confirm_password: confirmPassword || password,
    };

    if (!payload.first_name || !payload.last_name || !payload.email || !payload.mobile || !payload.password) {
      setAlert({ type: 'danger', message: 'All fields are required' });
      return;
    }
    try {
      const res = await fetch('http://127.0.0.1:5000/api/automation/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://qa.systemisers.in/', headless, ...payload })
      });
      const json = await res.json().catch(() => null);
      if (res.ok && json?.success) {
        setAlert({ type: 'success', message: json.message || 'Sign-up automation completed successfully' });
        setShowResult({ title: 'Output', output: json.output || '' });
      } else {
        const msg = json?.message || json?.error || 'Sign-up failed';
        setAlert({ type: 'danger', message: msg });
        setShowResult({ title: 'Error', error: json?.error || '', output: json?.output || '' });
      }
    } catch (e: any) {
      setAlert({ type: 'danger', message: 'Request failed' });
      setShowResult({ title: 'Error', error: String(e) });
    }
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = new Uint8Array(ev.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json<any>(ws);
        const parsed = json.map((r: any, i: number) => ({
          id: `row-${Date.now()}-${i}`,
          FirstName: r.FirstName || r['First Name'] || '',
          LastName: r.LastName || r['Last Name'] || '',
          Email: r.Email || '',
          Mobile: r.Mobile || r['Mobile Number'] || '',
          Password: r.Password || '',
          ConfirmPassword: r.ConfirmPassword || r['Confirm Password'] || ''
        }));
        setRows(parsed);
        setAlert({ type: 'success', message: `Loaded ${parsed.length} rows` });
      } catch {
        setAlert({ type: 'danger', message: 'Invalid Excel file' });
      }
    };
    reader.readAsArrayBuffer(file);
  };

  return (
    <Row>
      <Col md={2}>
        <SideBar />
      </Col>
      <Col>
        <Container fluid className="py-4">
          <Card className="mb-4">
            <Card.Header className="d-flex align-items-center justify-content-between">
              <h5 className="mb-0">Sign Up</h5>
              <Form.Check type="switch" id="signup-headless" label="Headless" checked={headless} onChange={(e) => setHeadless(e.target.checked)} />
            </Card.Header>
            <Card.Body>
              {alert && <Alert variant={alert.type} onClose={() => setAlert(null)} dismissible>{alert.message}</Alert>}
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-2">
                    <Form.Label>First Name</Form.Label>
                    <Form.Control placeholder="Enter first name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                  </Form.Group>
                  <Form.Group className="mb-2">
                    <Form.Label>Last Name</Form.Label>
                    <Form.Control placeholder="Enter last name" value={lastName} onChange={(e) => setLastName(e.target.value)} />
                  </Form.Group>
                  <Form.Group className="mb-2">
                    <Form.Label>Email</Form.Label>
                    <Form.Control type="email" placeholder="Enter email address" value={email} onChange={(e) => setEmail(e.target.value)} />
                  </Form.Group>
                  <Form.Group className="mb-2">
                    <Form.Label>Mobile</Form.Label>
                    <Form.Control placeholder="Enter mobile number" value={mobile} onChange={(e) => setMobile(e.target.value)} />
                  </Form.Group>
                  <Form.Group className="mb-2">
                    <Form.Label>Password</Form.Label>
                    <Form.Control type="password" placeholder="Enter password" value={password} onChange={(e) => setPassword(e.target.value)} />
                  </Form.Group>
                  <Form.Group className="mb-3">
                    <Form.Label>Confirm Password</Form.Label>
                    <Form.Control type="password" placeholder="Re-enter password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                  </Form.Group>
                  <Button onClick={() => runSignup()} variant="primary">Run Sign-Up</Button>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Upload Excel</Form.Label>
                    <Form.Control type="file" accept=".xlsx,.xls" ref={fileRef} onChange={handleUpload} />
                  </Form.Group>
                  {rows.length > 0 && (
                    <Table striped bordered hover size="sm" className="mt-3">
                      <thead>
                        <tr><th>First</th><th>Last</th><th>Email</th><th>Mobile</th><th>Action</th></tr>
                      </thead>
                      <tbody>
                        {rows.map((r) => (
                          <tr key={r.id}>
                            <td>{r.FirstName}</td>
                            <td>{r.LastName}</td>
                            <td>{r.Email}</td>
                            <td>{r.Mobile}</td>
                            <td><Button size="sm" onClick={() => runSignup(r)}>Run</Button></td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Col>
              </Row>
              {showResult && (
                <Alert variant={showResult.error ? 'danger' : 'info'} className="mt-3">
                  <div className="fw-semibold mb-1">{showResult.title}</div>
                  {showResult.output && <pre className="bg-light p-2 rounded">{showResult.output}</pre>}
                  {showResult.error && <pre className="bg-light p-2 rounded text-danger">{showResult.error}</pre>}
                </Alert>
              )}
            </Card.Body>
          </Card>
        </Container>
      </Col>
    </Row>
  );
};

export default SignUp;
