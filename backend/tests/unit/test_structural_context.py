import pytest
import uuid
from app.modules.indexing.chunking.context import StructuralContextExtractor, extract_module_name
from app.modules.repositories.models import CodeSymbol

def test_python_context():
    # class AuthService:
    #     def authenticate_user(self):
    #         pass
    
    file_id = uuid.uuid4()
    
    class_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="AuthService",
        symbol_type="CLASS",
        language="python",
        start_line=1, end_line=3, start_column=0, end_column=0
    )
    
    method_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        parent_symbol_id=class_sym.id,
        name="authenticate_user",
        symbol_type="METHOD",
        language="python",
        start_line=2, end_line=3, start_column=4, end_column=16
    )
    
    extractor = StructuralContextExtractor([class_sym, method_sym])
    
    ctx = extractor.extract_context(method_sym, "backend/auth/service.py")
    assert ctx["class_name"] == "AuthService"
    assert ctx["parent_symbol"] == "AuthService"
    assert ctx["context_path"] == "AuthService.authenticate_user"
    assert ctx["module_name"] == "backend.auth.service"
    
    # Check top-level class
    ctx_class = extractor.extract_context(class_sym, "backend/auth/service.py")
    assert ctx_class["class_name"] == "AuthService"
    assert ctx_class["parent_symbol"] is None
    assert ctx_class["context_path"] == "AuthService"

def test_java_context():
    file_id = uuid.uuid4()
    
    class_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="AuthService",
        symbol_type="CLASS",
        language="java",
        start_line=1, end_line=3, start_column=0, end_column=0
    )
    
    method_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        parent_symbol_id=class_sym.id,
        name="authenticateUser",
        symbol_type="METHOD",
        language="java",
        start_line=2, end_line=3, start_column=4, end_column=16
    )
    
    extractor = StructuralContextExtractor([class_sym, method_sym])
    
    ctx = extractor.extract_context(method_sym, "src/main/java/com/example/auth/AuthService.java")
    assert ctx["class_name"] == "AuthService"
    assert ctx["context_path"] == "AuthService.authenticateUser"
    assert ctx["module_name"] == "com.example.auth.AuthService"

def test_javascript_context():
    file_id = uuid.uuid4()
    
    class_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="UserController",
        symbol_type="CLASS",
        language="javascript",
        start_line=1, end_line=10, start_column=0, end_column=0
    )
    
    method_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        parent_symbol_id=class_sym.id,
        name="login",
        symbol_type="METHOD",
        language="javascript",
        start_line=2, end_line=5, start_column=4, end_column=5
    )
    
    extractor = StructuralContextExtractor([class_sym, method_sym])
    ctx = extractor.extract_context(method_sym, "src/controllers/user.js")
    assert ctx["class_name"] == "UserController"
    assert ctx["context_path"] == "UserController.login"
    assert ctx["module_name"] == "src.controllers.user"

def test_rust_context():
    file_id = uuid.uuid4()
    
    impl_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="User",
        symbol_type="IMPL",
        language="rust",
        start_line=1, end_line=10, start_column=0, end_column=0
    )
    
    method_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        parent_symbol_id=impl_sym.id,
        name="new",
        symbol_type="METHOD",
        language="rust",
        start_line=2, end_line=5, start_column=4, end_column=5
    )
    
    extractor = StructuralContextExtractor([impl_sym, method_sym])
    ctx = extractor.extract_context(method_sym, "src/models/user.rs")
    assert ctx["class_name"] == "User"  # IMPL is mapped to class_name implicitly because it's class-like structure
    assert ctx["context_path"] == "User.new"
    
def test_go_context():
    file_id = uuid.uuid4()
    
    func_sym = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="RunIngestion",
        symbol_type="FUNCTION",
        language="go",
        start_line=1, end_line=10, start_column=0, end_column=0
    )
    
    extractor = StructuralContextExtractor([func_sym])
    ctx = extractor.extract_context(func_sym, "worker/ingest.go")
    assert ctx["class_name"] is None
    assert ctx["context_path"] == "RunIngestion"
    assert ctx["module_name"] == "worker.ingest"

def test_nested_functions():
    file_id = uuid.uuid4()
    
    func1 = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        name="outer",
        symbol_type="FUNCTION",
        language="python",
        start_line=1, end_line=5, start_column=0, end_column=0
    )
    
    func2 = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=file_id,
        parent_symbol_id=func1.id,
        name="inner",
        symbol_type="FUNCTION",
        language="python",
        start_line=2, end_line=4, start_column=4, end_column=4
    )
    
    extractor = StructuralContextExtractor([func1, func2])
    ctx = extractor.extract_context(func2, "nested.py")
    assert ctx["class_name"] is None
    assert ctx["parent_symbol"] == "outer"
    assert ctx["context_path"] == "outer.inner"
