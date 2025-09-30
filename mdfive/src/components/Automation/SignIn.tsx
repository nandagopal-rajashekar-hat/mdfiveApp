import React, { useState, useRef } from 'react';
import { Container, Row, Col, Card, Button, Alert, Form, Table, Modal } from 'react-bootstrap';
import { FaFileExcel, FaSignInAlt, FaEye, FaEyeSlash, FaUpload, FaTrash } from 'react-icons/fa';
import * as XLSX from 'xlsx';
import SideBar from '../SideBar';

// Define types locally to avoid import issues
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

interface SignInResult {
  success: boolean;
  message: string;
  credential?: Credential;
}

const SignIn: React.FC = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null);
  const [showPassword, setShowPassword] = useState<{ [key: string]: boolean }>({});
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'danger' | 'warning'; message: string } | null>(null);
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
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
        const jsonData = XLSX.utils.sheet_to_json<ExcelCredentialData>(worksheet);

        const parsedCredentials: Credential[] = jsonData.map((row, index) => ({
          id: `credential-${Date.now()}-${index}`,
          email: row.Email || '',
          password: row.Password || '',
          name: row.Name || `Credential ${index + 1}`,
          description: row.Description || ''
        }));

        setCredentials(parsedCredentials);
        setAlert({ type: 'success', message: `Successfully loaded ${parsedCredentials.length} credentials from Excel file` });
      } catch (error) {
        setAlert({ type: 'danger', message: 'Error reading Excel file. Please check the format.' });
      }
    };
    reader.readAsArrayBuffer(file);
  };

  const togglePasswordVisibility = (credentialId: string) => {
    setShowPassword(prev => ({
      ...prev,
      [credentialId]: !prev[credentialId]
    }));
  };

  const deleteCredential = (credentialId: string) => {
    setCredentials(prev => prev.filter(cred => cred.id !== credentialId));
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
      // Call the Flask API endpoint
      const response = await fetch('http://localhost:5001/api/automation/signin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: selectedCredential.email,
          password: selectedCredential.password,
          url: 'https://qa.systemisers.in/'
        })
      });

      if (response.ok) {
        const result: SignInResult = await response.json();
        setAlert({ type: 'success', message: result.message });
      } else {
        setAlert({ type: 'danger', message: 'Sign-in failed. Please check your credentials.' });
      }
    } catch (error) {
      setAlert({ type: 'danger', message: 'Error during sign-in process. Please try again.' });
    } finally {
      setIsSigningIn(false);
      setShowCredentialModal(false);
    }
  };

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
    <>
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

                    {/* File Upload Section */}
                    <Row className="mb-4">
                      <Col md={6}>
                        <Card>
                          <Card.Header>
                            <h5>Upload Credentials from Excel</h5>
                          </Card.Header>
                          <Card.Body>
                            <Form.Group className="mb-3">
                              <Form.Label>Select Excel File</Form.Label>
                              <Form.Control
                                type="file"
                                accept=".xlsx,.xls"
                                onChange={handleFileUpload}
                                ref={fileInputRef}
                              />
                              <Form.Text className="text-muted">
                                Upload an Excel file with columns: Email, Password, Name (optional), Description (optional)
                              </Form.Text>
                            </Form.Group>
                            <Button 
                              variant="primary" 
                              onClick={() => fileInputRef.current?.click()}
                              disabled={isSigningIn}
                            >
                              <FaUpload className="me-2" />
                              Choose File
                            </Button>
                          </Card.Body>
                        </Card>
                      </Col>
                      <Col md={6}>
                        <Card>
                          <Card.Header>
                            <h5>Instructions</h5>
                          </Card.Header>
                          <Card.Body>
                            <ol>
                              <li>Download the sample Excel template</li>
                              <li>Fill in your credentials (Email, Password, Name, Description)</li>
                              <li>Upload the Excel file</li>
                              <li>Select a credential and click Sign In</li>
                            </ol>
                            <Alert variant="info" className="mt-3">
                              <strong>Note:</strong> The system will use Selenium automation to sign in to the target website.
                            </Alert>
                          </Card.Body>
                        </Card>
                      </Col>
                    </Row>

                    {/* Credentials Table */}
                    {credentials.length > 0 && (
                      <Row>
                        <Col md={12}>
                          <Card>
                            <Card.Header>
                              <h5>Loaded Credentials ({credentials.length})</h5>
                            </Card.Header>
                            <Card.Body>
                              <Table striped bordered hover responsive>
                                <thead>
                                  <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Password</th>
                                    <th>Description</th>
                                    <th>Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {credentials.map((credential) => (
                                    <tr key={credential.id}>
                                      <td>{credential.name}</td>
                                      <td>{credential.email}</td>
                                      <td>
                                        <div className="d-flex align-items-center">
                                          <span className="me-2">
                                            {showPassword[credential.id] 
                                              ? credential.password 
                                              : '•'.repeat(credential.password.length)
                                            }
                                          </span>
                                          <Button
                                            variant="outline-secondary"
                                            size="sm"
                                            onClick={() => togglePasswordVisibility(credential.id)}
                                          >
                                            {showPassword[credential.id] ? <FaEyeSlash /> : <FaEye />}
                                          </Button>
                                        </div>
                                      </td>
                                      <td>{credential.description}</td>
                                      <td>
                                        <div className="d-flex gap-2">
                                          <Button
                                            variant="success"
                                            size="sm"
                                            onClick={() => selectCredential(credential)}
                                            disabled={isSigningIn}
                                          >
                                            <FaSignInAlt className="me-1" />
                                            Sign In
                                          </Button>
                                          <Button
                                            variant="danger"
                                            size="sm"
                                            onClick={() => deleteCredential(credential.id)}
                                          >
                                            <FaTrash />
                                          </Button>
                                        </div>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </Table>
                            </Card.Body>
                          </Card>
                        </Col>
                      </Row>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            {/* Sign In Confirmation Modal */}
            <Modal show={showCredentialModal} onHide={() => setShowCredentialModal(false)}>
              <Modal.Header closeButton>
                <Modal.Title>Confirm Sign-In</Modal.Title>
              </Modal.Header>
              <Modal.Body>
                {selectedCredential && (
                  <div>
                    <p><strong>Name:</strong> {selectedCredential.name}</p>
                    <p><strong>Email:</strong> {selectedCredential.email}</p>
                    <p><strong>Description:</strong> {selectedCredential.description}</p>
                    <Alert variant="warning">
                      <strong>Warning:</strong> This will trigger automated sign-in using Selenium. 
                      Make sure you have the necessary permissions and the target website is accessible.
                    </Alert>
                  </div>
                )}
              </Modal.Body>
              <Modal.Footer>
                <Button variant="secondary" onClick={() => setShowCredentialModal(false)}>
                  Cancel
                </Button>
                <Button 
                  variant="primary" 
                  onClick={executeSignIn}
                  disabled={isSigningIn}
                >
                  {isSigningIn ? 'Signing In...' : 'Confirm Sign-In'}
                </Button>
              </Modal.Footer>
            </Modal>
          </Container>
        </Col>
      </Row>
    </>
  );
};

export default SignIn;