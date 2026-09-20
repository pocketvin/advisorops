import type { ImageAttachmentInput } from "./api";

const ACCEPTED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_FILES = 4;
const MAX_ORIGINAL_BYTES = 10 * 1024 * 1024;
const MAX_INLINE_BYTES = 3 * 1024 * 1024;

function readAsDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsDataURL(file);
  });
}

async function compressImage(file: File): Promise<ImageAttachmentInput> {
  if (!ACCEPTED.has(file.type)) {
    throw new Error("仅支持 JPEG、PNG、WebP 图片");
  }
  if (file.size > MAX_ORIGINAL_BYTES) {
    throw new Error("单张图片不能超过 10MB");
  }

  if (file.size <= MAX_INLINE_BYTES) {
    return {
      name: file.name,
      mime_type: file.type as ImageAttachmentInput["mime_type"],
      data_url: await readAsDataUrl(file),
    };
  }

  const bitmap = await createImageBitmap(file);
  const longest = Math.max(bitmap.width, bitmap.height);
  const scale = longest > 1800 ? 1800 / longest : 1;
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器无法处理这张图片");
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (value) => (value ? resolve(value) : reject(new Error("图片压缩失败"))),
      "image/jpeg",
      0.88,
    );
  });

  return {
    name: file.name.replace(/\.[^.]+$/, "") + ".jpg",
    mime_type: "image/jpeg",
    data_url: await readAsDataUrl(blob),
  };
}

export async function prepareImageAttachments(
  files: FileList | File[],
  existingCount = 0,
): Promise<ImageAttachmentInput[]> {
  const selected = Array.from(files);
  if (existingCount + selected.length > MAX_FILES) {
    throw new Error("单次最多上传 4 张图片");
  }
  return Promise.all(selected.map(compressImage));
}

export function attachmentPreviewUrl(
  attachment: ImageAttachmentInput,
): string {
  return attachment.data_url;
}
