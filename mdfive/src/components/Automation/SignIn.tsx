import React, { useEffect, useState, useRef } from 'react';
import { Container, Row, Col, Card, Button, Alert, Form, Table, Modal } from 'react-bootstrap';
import { FaFileExcel, FaSignInAlt, FaEye, FaEyeSlash, FaTrash } from 'react-icons/fa';
import * as XLSX from 'xlsx';
import SideBar from '../SideBar';

class PageErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error?: any }>{
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, info: any) {
    console.error('Automation page render error:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <Container className="py-4">
          <Alert variant="danger">
            <div className="fw-bold mb-2">Automation page failed to render.</div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{String(this.state.error)}</div>
          </Alert>
        </Container>
      );
    }
    return <>{this.props.children}</>;
  }
}

interface Credential {
  id: string;
  email: string;
  password: string;
  name?: string;
  description?: string;
}

interface ExcelCredentialData {
  Email: string;
  Password: string;
  Name?: string;
  Description?: string;
}

// removed unused SignInResult

const SignIn: React.FC = () => {
  // Removed unused credentials state (Excel table now uses signInExcelCreds)
  // const [credentials, setCredentials] = useState<Credential[]>([]);
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null);
  const [showPassword, setShowPassword] = useState<{ [key: string]: boolean }>({});
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger' | 'warning'; message: string } | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);
  const [resultTitle, setResultTitle] = useState<string>('');
  const [resultOutput, setResultOutput] = useState<string>('');
  const [resultError, setResultError] = useState<string>('');
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  // removed unused file input ref
  const [manualEmail, setManualEmail] = useState<string>('');
  const [manualPassword, setManualPassword] = useState<string>('');
  const [signinHeadless, setSigninHeadless] = useState<boolean>(true);
  const signInFileRef = useRef<HTMLInputElement>(null);
  const [signInExcelCreds, setSignInExcelCreds] = useState<Credential[]>([]);

  // Sign-up row typing is not required on this page

  const handleSignInFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' &&
      file.type !== 'application/vnd.ms-excel') {
      setAlert({ type: 'danger', message: 'Please upload a valid Excel file (.xlsx or .xls)' });
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json<any>(worksheet);

        const parsedCredentials: Credential[] = jsonData.map((row: ExcelCredentialData, index: number) => ({
          id: `credential-${Date.now()}-${index}`,
          email: row.Email || '',
          password: row.Password || '',
          name: row.Name || `Credential ${index + 1}`,
          description: row.Description || ''
        }));

        setSignInExcelCreds(parsedCredentials);
        setAlert({ type: 'success', message: `Loaded ${parsedCredentials.length} sign-in credentials` });
      } catch (error) {
        setAlert({ type: 'danger', message: 'Error reading Excel file. Please check the format.' });
      }
    };
    reader.readAsArrayBuffer(file);
  };

  // Sign-up upload removed from this page (moved to dedicated SignUp page)

  const togglePasswordVisibility = (credentialId: string) => {
    setShowPassword(prev => ({
      ...prev,
      [credentialId]: !prev[credentialId]
    }));
  };

  const deleteCredential = (credentialId: string) => {
    setSignInExcelCreds(prev => prev.filter((cred: Credential) => cred.id !== credentialId));
    setAlert({ type: 'warning', message: 'Credential deleted successfully' });
  };

  const selectCredential = (credential: Credential) => {
    setSelectedCredential(credential);
    setShowCredentialModal(true);
  };

  const executeSignIn = async () => {
    if (!selectedCredential) return;

    setIsSigningIn(true);
    setAlert(null);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/automation/signin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: selectedCredential.email,
          password: selectedCredential.password,
          url: 'https://qa.systemisers.in/',
          headless: signinHeadless
        })
      });

      const resultJson = await response.json().catch(() => null);
      const success = response.ok && resultJson && resultJson.success;

      if (success) {
        setAlert({ type: 'success', message: resultJson.message || 'Sign-in automation completed successfully' });
        setResultTitle('Automation Output');
        setResultOutput((resultJson.output ?? '').toString());
        setResultError('');
        setShowResultModal(true);
      } else {
        const errorMessage = (resultJson && (resultJson.message || resultJson.error)) || 'Sign-in failed. Please check your credentials.';
        setAlert({ type: 'danger', message: errorMessage });
        setResultTitle('Automation Result');
        setResultOutput(((resultJson && resultJson.output) ?? '').toString());
        setResultError(((resultJson && resultJson.error) ?? '').toString());
        setShowResultModal(true);
      }
    } catch (error) {
      setAlert({ type: 'danger', message: 'Error during sign-in process. Please try again.' });
      setResultTitle('Automation Error');
      setResultOutput('');
      setResultError((error as Error).message);
      setShowResultModal(true);
    } finally {
      setIsSigningIn(false);
      setShowCredentialModal(false);
    }
  };

  const executeManualSignIn = async (email: string, password: string) => {
    if (!email || !password) {
      setAlert({ type: 'danger', message: 'Email and password are required' });
      return;
    }
    setIsSigningIn(true);
    setAlert(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/automation/signin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, url: 'https://qa.systemisers.in/', headless: signinHeadless })
      });
      const resultJson = await response.json().catch(() => null);
      const success = response.ok && resultJson && resultJson.success;
      if (success) {
        setAlert({ type: 'success', message: resultJson.message || 'Sign-in automation completed successfully' });
        setResultTitle('Automation Output');
        setResultOutput((resultJson.output ?? '').toString());
        setResultError('');
      } else {
        const errorMessage = (resultJson && (resultJson.message || resultJson.error)) || 'Sign-in failed.';
        setAlert({ type: 'danger', message: errorMessage });
        setResultTitle('Automation Result');
        setResultOutput(((resultJson && resultJson.output) ?? '').toString());
        setResultError(((resultJson && resultJson.error) ?? '').toString());
      }
      setShowResultModal(true);
    } catch (error) {
      setAlert({ type: 'danger', message: 'Error during sign-in process. Please try again.' });
      setResultTitle('Automation Error');
      setResultOutput('');
      setResultError((error as Error).message);
      setShowResultModal(true);
    } finally {
      setIsSigningIn(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlEmail = params.get('email');
    const urlPassword = params.get('password');
    const auto = params.get('auto');
    if (auto === 'true' && urlEmail && urlPassword) {
      setManualEmail(urlEmail);
      setManualPassword(urlPassword);
      executeManualSignIn(urlEmail, urlPassword);
    }
  }, []);

  // Sign-up execution removed from this page (use /automation/signup)

  // Sign-up per-row execution removed from this page (use /automation/signup)

  const downloadSampleExcel = () => {
    const sampleData = [
      { Email: 'user1@example.com', Password: 'password123', Name: 'Test User 1', Description: 'Primary test account' },
      { Email: 'user2@example.com', Password: 'password456', Name: 'Test User 2', Description: 'Secondary test account' }
    ];

    const worksheet = XLSX.utils.json_to_sheet(sampleData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Credentials');
    XLSX.writeFile(workbook, 'credentials_sample.xlsx');
  };

  return (
    <PageErrorBoundary>
      <Row>
        <Col md={2}>
          <SideBar />
        </Col>
        <Col>
          <Container fluid className="py-4">
            <Row>
              <Col md={12}>
                <Card>
                  <Card.Header className="d-flex justify-content-between align-items-center">
                    <h4 className="mb-0">
                      <FaSignInAlt className="me-2" />
                      Automation Sign-In
                    </h4>
                    <Button variant="outline-primary" onClick={downloadSampleExcel}>
                      <FaFileExcel className="me-2" />
                      Download Sample Excel
                    </Button>
                  </Card.Header>
                  <Card.Body>
                    {alert && (
                      <Alert variant={alert.type} dismissible onClose={() => setAlert(null)}>
                        {alert.message}
                      </Alert>
                    )}

                    {/* Manual Trigger Section */}
                    <Row className="mb-4">
                      <Col md={6}>
                        <Card>
                          <Card.Header>
                            <div className="d-flex align-items-center justify-content-between">
                              <h5 className="mb-0">Quick Automation</h5>
                              <Form.Check
                                type="switch"
                                id="headless-switch"
                                label="Headless"
                                checked={signinHeadless}
                                onChange={(e) => setSigninHeadless(e.target.checked)}
                              />
                            </div>
                          </Card.Header>
                          <Card.Body>
                            <Form.Group className="mb-3">
                              <Form.Label>Email</Form.Label>
                              <Form.Control type="email" value={manualEmail} onChange={(e) => setManualEmail(e.target.value)} placeholder="Enter email" />
                            </Form.Group>
                            <Form.Group className="mb-3">
                              <Form.Label>Password</Form.Label>
                              <Form.Control type="password" value={manualPassword} onChange={(e) => setManualPassword(e.target.value)} placeholder="Enter password" />
                            </Form.Group>
                            <div className="d-flex gap-2">
                              <Button variant="success" disabled={isSigningIn} onClick={() => executeManualSignIn(manualEmail, manualPassword)}>
                                {isSigningIn ? 'Running...' : 'Run Automation'}
                              </Button>
                              <Form.Text className="text-muted">Use this for quick testing with manual credentials</Form.Text>
                            </div>
                          </Card.Body>
                        </Card>
                      </Col>

                      {/* Excel Upload Section */}
                      <Col md={6}>
                        <Card>
                          <Card.Header>
                            <h5 className="mb-0">Upload Excel Credentials</h5>
                          </Card.Header>
                          <Card.Body>
                            <Form.Group>
                              <Form.Label>Upload Excel file</Form.Label>
                              <Form.Control type="file" accept=".xlsx,.xls" ref={signInFileRef} onChange={handleSignInFileUpload} />
                            </Form.Group>
                            {signInExcelCreds.length > 0 && (
                              <Table striped bordered hover size="sm" className="mt-3">
                                <thead>
                                  <tr>
                                    <th>Email</th>
                                    <th>Password</th>
                                    <th>Name</th>
                                    <th>Action</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {signInExcelCreds.map((cred) => (
                                    <tr key={cred.id}>
                                      <td>{cred.email}</td>
                                      <td>{cred.password.replace(/./g, '*')}</td>
                                      <td>{cred.name}</td>
                                      <td>
                                        <Button size="sm" variant="primary" onClick={() => selectCredential(cred)}>
                                          Run
                                        </Button>
                                        <Button size="sm" variant="danger" className="ms-2" onClick={() => deleteCredential(cred.id)}>
                                          <FaTrash />
                                        </Button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </Table>
                            )}
                          </Card.Body>
                        </Card>
                      </Col>
                    </Row>

                    {/* Sign-Up UI moved to dedicated page at /automation/signup */}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Container>

          {/* Credential Modal */}
          <Modal show={showCredentialModal} onHide={() => setShowCredentialModal(false)}>
            <Modal.Header closeButton>
              <Modal.Title>Credential Details</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              {selectedCredential && (
                <>
                  <p><strong>Email:</strong> {selectedCredential.email}</p>
                  <p><strong>Password:</strong> {showPassword[selectedCredential.id] ? selectedCredential.password : '********'}</p>
                  <p><strong>Name:</strong> {selectedCredential.name}</p>
                  <p><strong>Description:</strong> {selectedCredential.description}</p>
                  <Button variant="outline-secondary" onClick={() => togglePasswordVisibility(selectedCredential.id)} className="me-2">
                    {showPassword[selectedCredential.id] ? <FaEyeSlash /> : <FaEye />}
                  </Button>
                </>
              )}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setShowCredentialModal(false)}>Close</Button>
              <Button variant="primary" disabled={isSigningIn} onClick={executeSignIn}>
                {isSigningIn ? 'Signing In...' : 'Sign In'}
              </Button>
            </Modal.Footer>
          </Modal>

          {/* Result Modal */}
          <Modal show={showResultModal} onHide={() => setShowResultModal(false)} size="lg">
            <Modal.Header closeButton>
              <Modal.Title>{resultTitle}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              {resultOutput && (
                <div className="mb-3">
                  <h6>Output:</h6>
                  <pre className="bg-light p-2 rounded">{resultOutput}</pre>
                </div>
              )}
              {resultError && (
                <div className="mb-3">
                  <h6>Error:</h6>
                  <pre className="bg-light p-2 rounded text-danger">{resultError}</pre>
                </div>
              )}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setShowResultModal(false)}>Close</Button>
            </Modal.Footer>
          </Modal>
        </Col>
      </Row>
    </PageErrorBoundary>
  );
};

export default SignIn;
