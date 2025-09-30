import React, { useRef, useState } from 'react';
import { Alert, Button, Card, Col, Container, Form, Row, Table } from 'react-bootstrap';
import * as XLSX from 'xlsx';
import SideBar from '../SideBar';

interface ExcelForgotRow { Email?: string }

const Forgot: React.FC = () => {
  const [email, setEmail] = useState('');
  const [headless, setHeadless] = useState(true);
  const [rows, setRows] = useState<Array<ExcelForgotRow & { id: string }>>([]);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger' | 'warning'; message: string } | null>(null);
  const [result, setResult] = useState<string>('');
  const fileRef = useRef<HTMLInputElement>(null);

  const runForgot = async (targetEmail?: string) => {
    const e = targetEmail || email;
    if (!e) { setAlert({ type: 'danger', message: 'Email is required' }); return; }
    try {
      const res = await fetch('http://127.0.0.1:5000/api/automation/forgot', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: e, headless })
      });
      const json = await res.json().catch(() => null);
      setResult(JSON.stringify(json || {}, null, 2));
      if (res.ok && json?.success) setAlert({ type: 'success', message: json.message || 'Forgot password automation executed' });
      else setAlert({ type: 'danger', message: json?.message || json?.error || 'Forgot password failed' });
    } catch (err: any) {
      setAlert({ type: 'danger', message: String(err) });
    }
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = new Uint8Array(ev.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json<any>(ws);
        const parsed = json.map((r: any, i: number) => ({ id: `f-${Date.now()}-${i}`, Email: r.Email || '' }));
        setRows(parsed);
        setAlert({ type: 'success', message: `Loaded ${parsed.length} emails` });
      } catch { setAlert({ type: 'danger', message: 'Invalid Excel file' }); }
    };
    reader.readAsArrayBuffer(file);
  };

  return (
    <Row>
      <Col md={2}><SideBar /></Col>
      <Col>
        <Container fluid className="py-4">
          <Card>
            <Card.Header className="d-flex align-items-center justify-content-between">
              <h5 className="mb-0">Forgot Password</h5>
              <Form.Check type="switch" id="forgot-headless" label="Headless" checked={headless} onChange={(e) => setHeadless(e.target.checked)} />
            </Card.Header>
            <Card.Body>
              {alert && <Alert variant={alert.type} dismissible onClose={() => setAlert(null)}>{alert.message}</Alert>}
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3"><Form.Label>Email</Form.Label><Form.Control type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Form.Group>
                  <Button variant="primary" onClick={() => runForgot()}>Run Forgot Flow</Button>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-2"><Form.Label>Upload Excel</Form.Label><Form.Control type="file" accept=".xlsx,.xls" ref={fileRef} onChange={handleUpload} /></Form.Group>
                  {rows.length > 0 && (
                    <Table striped bordered hover size="sm" className="mt-2">
                      <thead><tr><th>Email</th><th>Action</th></tr></thead>
                      <tbody>
                        {rows.map((r) => (
                          <tr key={r.id}><td>{r.Email}</td><td><Button size="sm" onClick={() => runForgot(r.Email || '')}>Run</Button></td></tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Col>
              </Row>
              {result && (<pre className="bg-light p-2 rounded mt-3">{result}</pre>)}
            </Card.Body>
          </Card>
        </Container>
      </Col>
    </Row>
  );
};

export default Forgot;


