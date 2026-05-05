#!/usr/bin/env python
"""Test script for registration endpoint"""
import requests
import time

# Wait for server to start
time.sleep(2)

try:
    response = requests.post('http://localhost:5000/auth/register', data={
        'nombre': 'Juan',
        'apellido': 'Perez',
        'email': 'juan@example.com',
        'password': 'Test1234!',
        'confirm_password': 'Test1234!',
        'rol': 'estudiante',
        'institucion_id': '1'
    }, timeout=5)
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response:\n{response.text}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
