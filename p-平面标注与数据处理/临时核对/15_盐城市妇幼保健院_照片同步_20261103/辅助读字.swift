import Foundation
import Vision
import ImageIO
let args = CommandLine.arguments.dropFirst()
for path in args {
    let url = URL(fileURLWithPath: path)
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.005
    do {
        try VNImageRequestHandler(url: url, options: [:]).perform([request])
        let rows = (request.results ?? []).map { result -> [String:Any] in
            let b = result.boundingBox
            return ["text": result.topCandidates(3).map { ["text":$0.string,"confidence":$0.confidence] }, "bbox": [b.origin.x, 1-b.origin.y-b.height, b.width, b.height]]
        }
        let data = try JSONSerialization.data(withJSONObject: ["file":url.lastPathComponent,"rows":rows],options:[.sortedKeys])
        print(String(data:data,encoding:.utf8)!)
    } catch { fputs("OCR error: \(url.lastPathComponent) \(error)\n",stderr) }
}
