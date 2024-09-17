# Do not rewrite this variable in your AI final response
swift_code_str = """
import SwiftUI
import SwiftData

// MARK: - Model
@Model
class Note {
    var title: String
    var content: String
    var date: Date

    init(title: String, content: String, date: Date = Date()) {
        self.title = title
        self.content = content
        self.date = date
    }

    func toString() -> String {
        return "Hello"
    }
}

// MARK: - ViewModel
@Observable class NotesViewModel {
    @Query 
    private var notes: [Note]
    let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    var sortedNotes: [Note] {
        notes.sorted { $0.date > $1.date }
    }

    func addNote(title: String, content: String) {
        let newNote = Note(title: title, content: content)
        modelContext.insert(newNote)
    }

    func updateNote(_ note: Note) {
        modelContext.insert(note)
    }

    func deleteNote(_ note: Note) {
        modelContext.delete(note)
    }
}

// MARK: - Views
struct ContentView: View {
    @Environment(\\.modelContext) private var modelContext
    @State private var viewModel: NotesViewModel
    @State private var showingAddNote = false

    init(modelContext: ModelContext) {
        _viewModel = State(initialValue: NotesViewModel(modelContext: modelContext))
    }

    var body: some View {
        NavigationView {
            List {
                ForEach(viewModel.sortedNotes) { note in
                    NavigationLink(destination: NoteDetailView(note: note, viewModel: viewModel)) {
                        VStack(alignment: .leading) {
                            Text(note.title)
                                .font(.headline)
                            Text(note.content)
                                .font(.subheadline)
                                .lineLimit(1)
                            Text(note.date, style: .date)
                                .font(.caption)
                        }
                    }
                }
                .onDelete(perform: deleteNotes)
            }
            .navigationTitle("Notes")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { showingAddNote = true }) {
                        Label("Add Note", systemImage: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddNote) {
                NoteDetailView(viewModel: viewModel)
            }
        }
    }

    private func deleteNotes(at offsets: IndexSet) {
        for index in offsets {
            viewModel.deleteNote(viewModel.sortedNotes[index])
        }
    }
}

struct NoteDetailView: View {
    @Environment(\\.dismiss) private var dismiss
    @State private var title: String
    @State private var content: String
    let note: Note?
    let viewModel: NotesViewModel

    init(note: Note? = nil, viewModel: NotesViewModel) {
        self.note = note
        self.viewModel = viewModel
        _title = State(initialValue: note?.title ?? "")
        _content = State(initialValue: note?.content ?? "")
    }

    var body: some View {
        NavigationView {
            Form {
                TextField("Title", text: $title)
                TextEditor(text: $content)
            }
            .navigationTitle(note == nil ? "Add Note" : "Edit Note")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        saveNote()
                        dismiss()
                    }
                }
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func saveNote() {
        if let note = note {
            note.title = title
            note.content = content
            note.date = Date()
            viewModel.updateNote(note)
        } else {
            viewModel.addNote(title: title, content: content)
        }
    }
}

private class PrivateClass: AnyObject {
    var prop: String { get set }
}

protocol ExampleProtocol: AnyObject {
    var protocolProperty: String { get set }
    func protocolMethod() throws -> Int
}

@objc public class ObjPubClass: NSObject, ExampleProtocol {
    // Simple property
    private let simpleProp: Int = 0

    // Property with annotation and optional type
    @available(*, deprecated, message: "Use newProp instead")
    public var oldProp: String?

    // Computed property
    public var computedProp: Double {
        get {
            return 3.14
        }
        set {
            print("Setting value: \(newValue)")
        }
    }

    // Property with observer
    public var observedProp: Bool = false {
        willSet {
            print("Will set observedProp to \(newValue)")
        }
        didSet {
            print("Did set observedProp from \(oldValue) to \(observedProp)")
        }
    }

    // Protocol property
    public var protocolProperty: String = "Hello, Protocol!"

    // Initializer
    public override init() {
        super.init()
    }

    // Deinitializer
    deinit {
        print("ExampleClass is being deinitialized")
    }

    // Method with complex return type and throws
    public func complexMethod<T: Comparable>(param: T) throws -> [String: [T]] {
        // Implementation
        return [:]
    }

    // Protocol method implementation
    public func protocolMethod() throws -> Int {
        // Implementation
        return 42
    }

    // Method with rethrows
    public func rethrowingMethod(callback: () throws -> Void) rethrows {
        try callback()
    }
}

// Extension
extension ExampleExtension {
    // Computed property in extension
    public var extensionProp: Int {
        return 100
    }

    // Method in extension
    internal func extensionMethod() {
        // Implementation
    }
}

// MARK: - App
@main
struct NotesApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView(modelContext: ModelContext(try! ModelContainer(for: Note.self)))
        }
    }
}
"""

# Do not rewrite this variable in your AI final response
desired_output = """
@Model
class Note
  var title: String
  var content: String
  var date: Date
  init(title: String, content: String, date: Date = Date())
  func toString() -> String

@Observable
class NotesViewModel
  @Query private var notes: [Note]
  let modelContext: ModelContext
  init(modelContext: ModelContext)
  var sortedNotes: [Note]
  func addNote(title: String, content: String)
  func updateNote(_ note: Note)
  func deleteNote(_ note: Note)

struct ContentView: View
  @Environment(\\.modelContext) private var modelContext
  @State private var viewModel: NotesViewModel
  @State private var showingAddNote: Bool
  init(modelContext: ModelContext)
  var body: some View
  private func deleteNotes(at offsets: IndexSet)

struct NoteDetailView: View
  @Environment(\\.dismiss) private var dismiss
  @State private var title: String
  @State private var content: String
  let note: Note?
  let viewModel: NotesViewModel
  init(note: Note? = nil, viewModel: NotesViewModel)
  var body: some View
  private func saveNote()

private class PrivateClass: AnyObject
  var prop: String { get set }

protocol ExampleProtocol: AnyObject
  var protocolProperty: String { get set }
  func protocolMethod() throws -> Int

@objc public class ObjPubClass: NSObject, ExampleProtocol
  private let simpleProp: Int
  @available(*, deprecated, message: "Use newProp instead")
  public var oldProp: String?
  public var computedProp: Double
  public var observedProp: Bool
  public var protocolProperty: String
  public override init()
  deinit
  public func complexMethod<T: Comparable>(param: T) throws -> [String: [T]]
  public func protocolMethod() throws -> Int
  public func rethrowingMethod(callback: () throws -> Void) rethrows

extension ExampleExtension
  public var extensionProp: Int
  internal func extensionMethod()

@main
struct NotesApp: App
  var body: some Scene
"""
